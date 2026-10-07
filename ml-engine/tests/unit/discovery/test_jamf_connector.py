"""The Jamf client and connector, against a fake Jamf.

The paging test is the one that matters most. `general.reportDate` is assigned at
check-in, so records shift between pages while a scan is reading them -- and the failure
mode is silent: the device is not seen again, and the fleet quietly shrinks. UP-4893 makes
a mid-pagination shift an acceptance criterion for exactly that reason.
"""

import base64
import dataclasses
import gzip
import io
import json
import logging
import re
import socket
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlsplit

import pytest
import requests
import yaml
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    EndpointAgentCreationSource,
    Platform,
    RunsOn,
    SourceAddress,
)
from urllib3.exceptions import LocationValueError

from discovery.endpoint.envelope import EnvelopeOutcome
from discovery.endpoint.jamf.client import JamfClient, JamfError, JamfSettings
from discovery.endpoint.jamf.connector import JamfConnector, _settings_from
from discovery.endpoint.records import records_for
from discovery.endpoint.scope import DeviceGroupError
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)

SCAN_AT = 1790100381
LOG = logging.getLogger("discovery-test")
CATALOG = yaml.safe_dump(
    {
        "version": 2,
        "classifications": ["Coding agent"],
        "agents": [
            {
                "id": "codex-cli",
                "name": "Codex CLI",
                "classification": "Coding agent",
                "platforms": ["darwin"],
                "npm": ["@openai/codex"],
                "binaries": ["~/.local/bin/codex"],
            },
        ],
    },
)
FIELDS = {"base_url": "https://acme.jamfcloud.com"}
CREDS = {
    "client_id": "id",
    "client_secret": "shh",
}


def frame(rows: list[dict[str, str]]) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(json.dumps(rows).encode())
    return "arthur1." + base64.b64encode(buf.getvalue()).decode()


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


def scan_row(branch: str, extra: str = "ok") -> dict[str, str]:
    return row("scan", branch, ver=str(SCAN_AT), extra=extra)


# Deliberately not the name any runbook suggests. The connector finds the payload by its
# `arthur1.` prefix, so a fleet that renamed its attributes is not a fleet it stops
# reading -- a test that used the documented name would pass either way.
EA_NAME = "Renamed By The Customer"


def computer(
    mid: str,
    value: Optional[str],
    report_date: str = "2026-09-22T10:00:00Z",
    ident: int = 0,
    extra_attributes: Optional[list[dict[str, Any]]] = None,
    groups: Optional[list[str]] = None,
) -> dict[str, Any]:
    record = {
        "id": ident or (abs(hash(mid)) % 100000),
        "general": {
            "managementId": mid,
            "name": f"mac-{mid}",
            "reportDate": report_date,
            "extensionAttributes": [
                {
                    "name": EA_NAME,
                    "values": [value] if value is not None else [],
                },
                *(extra_attributes or []),
            ],
        },
        "operatingSystem": {"name": "macOS", "version": "26.0"},
        "userAndLocation": {"username": "nori"},
        "hardware": {"serialNumber": f"SER{mid}"},
    }
    if groups is not None:
        # GROUP_MEMBERSHIPS, as Jamf returns it when the section is requested.
        record["groupMemberships"] = [
            {"groupId": gid, "groupName": f"group {gid}", "smartGroup": True}
            for gid in groups
        ]
    return record


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self) -> Any:
        return self._body


class FakeJamf:
    """A store that filters and sorts the way the real API does.

    Serves from a mutable device list so a test can have a device check in mid-scan,
    which is the only way to tell keyset paging from offset paging.
    """

    def __init__(
        self,
        pages: Optional[list[list[dict[str, Any]]]] = None,
        devices: Optional[list[dict[str, Any]]] = None,
        total: Optional[int] = None,
        get_statuses: Optional[list[int]] = None,
        page_size: int = 2,
        on_page: Optional[Any] = None,
        groups: Optional[list[dict[str, Any]]] = None,
        groups_status: int = 200,
    ) -> None:
        # `pages` is the simple form: whatever is listed comes back in order.
        self.pages = pages
        self.devices = devices or []
        self.page_size = page_size
        self.on_page = on_page
        self.total = total
        self.get_statuses = list(get_statuses or [])
        self.token_calls = 0
        self.gets: list[dict[str, Any]] = []
        self._calls = 0
        # GET /api/v1/computer-groups: an unpaginated list of every computer group.
        self.groups = groups or []
        self.groups_status = groups_status
        self.group_calls = 0

    def post(self, url: str, **kw: Any) -> FakeResponse:
        self.token_calls += 1
        return FakeResponse(
            200,
            {"access_token": f"tok{self.token_calls}", "expires_in": 3600},
        )

    @staticmethod
    def _key(d: dict[str, Any]) -> tuple[str, int]:
        return (d["general"]["reportDate"], int(d["id"]))

    def _after(
        self,
        cursor: Optional[tuple[str, Optional[int]]],
    ) -> list[dict[str, Any]]:
        rows = sorted(self.devices, key=self._key)
        if cursor is None:
            return rows
        date, ident = cursor
        if ident is None:
            return [d for d in rows if self._key(d)[0] > date]
        return [d for d in rows if self._key(d) > (date, ident)]

    def get(self, url: str, params: dict[str, Any], **kw: Any) -> FakeResponse:
        if url.endswith("/api/v1/computer-groups"):
            self.group_calls += 1
            if self.groups_status != 200:
                return FakeResponse(self.groups_status, None)
            return FakeResponse(200, self.groups)
        if self.get_statuses:
            status = self.get_statuses.pop(0)
            if status != 200:
                return FakeResponse(status, None, {"Retry-After": "0"})
        self.gets.append(dict(params))

        if self.pages is not None:
            # Served in sequence, not by params["page"]: keyset paging always sends
            # page 0 and advances by filter, so indexing on the page number would hand
            # back the same page forever.
            i = self._calls
            self._calls += 1
            results = self.pages[i] if i < len(self.pages) else []
            total = (
                sum(len(p) for p in self.pages) if self.total is None else self.total
            )
            return FakeResponse(200, {"totalCount": total, "results": results})

        where = params.get("filter")
        if where is not None and where.startswith("id=gt="):
            after = int(where.split("=gt=")[1])
            rows = sorted(self.devices, key=lambda d: int(d["id"]))
            results = [d for d in rows if int(d["id"]) > after][: self.page_size]
        elif where is None:  # first page of a roster walk
            rows = sorted(self.devices, key=lambda d: int(d["id"]))
            results = rows[: self.page_size]
        else:
            m = re.search(r'reportDate=gt="([^"]+)"', where)
            tie = re.search(r"id=gt=(\d+)", where)
            cursor = (m.group(1), int(tie.group(1)) if tie else None) if m else None
            results = self._after(cursor)[: self.page_size]

        self._calls += 1
        if self.on_page:
            self.on_page(self, self._calls)
        return FakeResponse(200, {"totalCount": len(self.devices), "results": results})


def client_for(fake: FakeJamf) -> JamfClient:
    return JamfClient(
        JamfSettings(**CREDS, **FIELDS, page_size=2),  # type: ignore[arg-type]
        session=fake,  # type: ignore[arg-type]
        sleep=lambda _s: None,
    )


# --- the client -------------------------------------------------------------------


def test_pages_until_totalcount_is_reached() -> None:
    fake = FakeJamf([[computer("a", None), computer("b", None)], [computer("c", None)]])
    assert [d.device_key for d in client_for(fake).devices_since(None)] == [
        "a",
        "b",
        "c",
    ]


def test_the_incremental_window_sorts_and_keys_on_the_same_pair() -> None:
    """The cursor is (reportDate, id), so the sort has to be too, or the next page's
    filter excludes rows the sort had not reached."""
    fake = FakeJamf([[computer("a", None)]])
    list(client_for(fake).devices_since("2026-09-22T09:00:00Z"))
    params = fake.gets[0]
    assert params["sort"] == "general.reportDate:asc,id:asc"
    assert "general.reportDate=gt=" in params["filter"]
    assert params["page"] == 0, "keyset restarts at page 0; the filter is the cursor"
    assert "EXTENSION_ATTRIBUTES" in params["section"]
    assert "GENERAL" in params["section"]


def test_a_full_enumeration_sends_no_filter_on_the_first_page() -> None:
    """The only thing that can answer which Macs stopped reporting at all."""
    fake = FakeJamf([[computer("a", None)]])
    list(client_for(fake).devices_since(None))
    assert "filter" not in fake.gets[0]


def test_a_device_checking_in_mid_scan_displaces_nobody() -> None:
    """The failure offset paging has and keyset paging does not.

    Ascending sort saves the record that checks in -- it moves to the end and is read
    again -- but under an OFFSET every record behind it shifts down one position, and at
    a page boundary one of them moves back into a page already read. Here `a` checks in
    after page 0, and `c` is the record that an offset would lose.
    """
    devices = [
        computer("a", None, "2026-09-22T09:00:00Z", ident=1),
        computer("b", None, "2026-09-22T09:00:01Z", ident=2),
        computer("c", None, "2026-09-22T09:00:02Z", ident=3),
        computer("d", None, "2026-09-22T09:00:03Z", ident=4),
    ]

    def check_in_after_first_page(fake: "FakeJamf", call: int) -> None:
        if call == 1:
            fake.devices[0]["general"]["reportDate"] = "2026-09-22T09:00:09Z"

    fake = FakeJamf(devices=devices, page_size=2, on_page=check_in_after_first_page)
    seen = [
        d.device_key for d in client_for(fake).devices_since("2026-09-22T08:00:00Z")
    ]

    assert "c" in seen, "a device behind the one that checked in must not be skipped"
    assert set(seen) >= {"a", "b", "c", "d"}
    assert seen.count("a") == 2, "the record that moved is simply read again"


def test_a_tie_on_report_date_does_not_stall_or_skip() -> None:
    """reportDate has second resolution and a fleet check-in lands many devices on one
    value. A cursor on the date alone would re-read them forever or skip the rest."""
    same = "2026-09-22T09:00:00Z"
    fake = FakeJamf(
        devices=[
            computer(c, None, same, ident=i) for i, c in enumerate("abcde", start=1)
        ],
        page_size=2,
    )
    seen = [
        d.device_key for d in client_for(fake).devices_since("2026-09-22T08:00:00Z")
    ]
    assert seen == ["a", "b", "c", "d", "e"]


def test_a_full_enumeration_pages_on_id_which_does_not_move() -> None:
    """Filtering on reportDate at all would drop devices that never reported, and those
    are exactly what a full enumeration is for."""
    fake = FakeJamf(
        devices=[
            computer(c, None, "2026-09-22T09:00:00Z", ident=i)
            for i, c in enumerate("abc", start=1)
        ],
        page_size=2,
    )
    seen = [d.device_key for d in client_for(fake).devices_since(None)]
    assert seen == ["a", "b", "c"]
    assert fake.gets[0]["sort"] == "id:asc"
    assert "filter" not in fake.gets[0]


def test_a_429_is_retried_honouring_retry_after() -> None:
    fake = FakeJamf([[computer("a", None)]], get_statuses=[429, 200])
    assert [d.device_key for d in client_for(fake).devices_since(None)] == ["a"]


def test_a_401_mid_scan_mints_a_fresh_token_and_retries() -> None:
    """The token can die between pages despite the 80% refresh."""
    fake = FakeJamf([[computer("a", None)]], get_statuses=[401, 200])
    list(client_for(fake).devices_since(None))
    assert fake.token_calls == 2


def test_a_token_is_reused_across_pages() -> None:
    fake = FakeJamf([[computer("a", None), computer("b", None)], [computer("c", None)]])
    list(client_for(fake).devices_since(None))
    assert fake.token_calls == 1


def test_a_non_retryable_status_fails_loudly() -> None:
    fake = FakeJamf([[computer("a", None)]], get_statuses=[403])
    with pytest.raises(JamfError, match="403"):
        list(client_for(fake).devices_since(None))


def test_a_failed_token_call_does_not_echo_the_response() -> None:
    class Denies(FakeJamf):
        def post(self, url: str, **kw: Any) -> FakeResponse:
            return FakeResponse(401, {"error": "client_secret=hunter2 was rejected"})

    fake = Denies([[]])
    with pytest.raises(JamfError) as exc:
        list(client_for(fake).devices_since(None))
    assert "hunter2" not in str(exc.value)
    # What the run reports as the credentials failing, not Jamf.
    assert exc.value.status_code == 401


# --- the connector ------------------------------------------------------------------


class FakeConfig:
    def __init__(self, query: Optional[str]) -> None:
        self.query = query
        self.vendor = "jamf_pro"
        self.name = "acme jamf"


def scan(fake: FakeJamf, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    connector = JamfConnector()
    return [r for batch in connector.scan(FakeConfig(CATALOG), 24, CREDS, FIELDS, LOG) for r in batch]  # type: ignore[arg-type]


def test_a_healthy_mac_yields_one_record_per_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = frame(
        [
            row("npm", "@openai/codex", ver="0.5.0"),
            row("file", "/Users/n/.local/bin/codex", loc="/Users/n/.local/bin/codex"),
            scan_row("packages"),
        ],
    )
    records = scan(FakeJamf([[computer("m1", payload)]]), monkeypatch)
    assert len(records) == 1, "two routes, one agent, one record"
    assert records[0].external_id == "m1:codex-cli"
    assert records[0].name == "Codex CLI"


def test_last_seen_is_the_scan_timestamp_not_the_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The payload dates itself. Using the poll time would date every record to now."""
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    records = scan(FakeJamf([[computer("m1", payload)]]), monkeypatch)
    assert records[0].last_seen == datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
    assert records[0].last_seen < datetime.now(timezone.utc)


@pytest.mark.parametrize(
    "value,because",
    [
        ("ERROR:oversize:271044", "the scan ran and its evidence would not fit"),
        ("no-cache", "the daemon never wrote"),
        (None, "Jamf has not heard from this Mac"),
        ("arthur1.@@@not-base64@@@", "bytes arrived that cannot be read"),
    ],
)
def test_an_unreadable_mac_yields_nothing_and_is_not_reported_as_clean(
    value: Optional[str],
    because: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[computer("m1", value)]]), monkeypatch)
    assert records == []
    assert "no usable payload" in caplog.text, because


def _ea(name: str, value: Optional[str]) -> dict[str, Any]:
    return {"name": name, "values": [value] if value is not None else []}


def test_the_payload_is_found_under_whatever_the_attribute_is_called(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`arthur1.` is a magic prefix so a reader can recognize the value without being
    told where to look. The display name is the admin's, and is not an input."""
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    for name in ("AI Inventory", "Arthur AI Inventory", "\u00e9v\u00e9nement", "x"):
        device = computer("m1", None)
        device["general"]["extensionAttributes"] = [_ea(name, payload)]
        records = scan(FakeJamf([[device]]), monkeypatch)
        assert [r.external_id for r in records] == ["m1:codex-cli"], name


def test_a_status_attribute_is_never_mistaken_for_the_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The status attribute sits beside the payload on every real device and carries a
    plain health line, which shares no prefix with a framed value."""
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    device = computer(
        "m1",
        payload,
        extra_attributes=[
            _ea("Arthur AI Inventory Status", "ok 2026-09-23T19:25:48Z apps=ok"),
            _ea("Arthur AI Osquery Prereq", "5.23.1"),
            _ea("Out of circulation", None),
        ],
    )
    records = scan(FakeJamf([[device]]), monkeypatch)
    assert [r.external_id for r in records] == ["m1:codex-cli"]


def test_no_cache_on_two_attributes_still_reports_no_cache(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A device whose collector never wrote puts `no-cache` on BOTH the payload and the
    status attribute, so the sentinel cannot identify which is which. It is read as a
    reason rather than as the payload, which keeps the deployment fault distinguishable
    from a Mac that has simply never reported."""
    device = computer("m1", "no-cache", extra_attributes=[_ea("Status", "no-cache")])
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[device]]), monkeypatch)
    assert records == []
    assert EnvelopeOutcome.NO_CACHE.value in caplog.text
    assert EnvelopeOutcome.NEVER_REPORTED.value not in caplog.text


def test_a_device_whose_attributes_are_all_empty_reads_as_never_reported(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    device = computer("m1", None, extra_attributes=[_ea("Status", None)])
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[device]]), monkeypatch)
    assert records == []
    assert EnvelopeOutcome.NEVER_REPORTED.value in caplog.text


def test_two_attributes_that_disagree_yield_nothing_rather_than_a_guess(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Nothing on the wire says which of two payloads is current, so taking either
    publishes a Mac's records from a source chosen by dictionary order."""
    first = frame([row("npm", "@openai/codex"), scan_row("packages")])
    second = frame([row("npm", "@anthropic-ai/claude-code"), scan_row("packages")])
    device = computer("m1", first, extra_attributes=[_ea("Second Collector", second)])
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[device]]), monkeypatch)
    assert records == []
    assert "disagree about this device's payload" in caplog.text
    assert "Second Collector" in caplog.text


def test_a_framed_payload_beside_an_oversize_marker_is_also_a_disagreement(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The marker carries neither content nor a date, so preferring the payload would
    still be a guess about which scan is the current one."""
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    device = computer(
        "m1",
        payload,
        extra_attributes=[_ea("Other", "ERROR:oversize:271044")],
    )
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[device]]), monkeypatch)
    assert records == []
    assert "disagree" in caplog.text


def test_duplicate_attributes_carrying_the_same_bytes_are_one_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two attributes running the same script read the same file, so identical
    candidates are one payload seen twice -- not a conflict."""
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    device = computer("m1", payload, extra_attributes=[_ea("A Copy", payload)])
    records = scan(FakeJamf([[device]]), monkeypatch)
    assert [r.external_id for r in records] == ["m1:codex-cli"]


def test_an_oversize_marker_is_found_by_its_prefix_too(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unframed on purpose so an MDM can match it without decoding -- which is also what
    lets this find it without being told the attribute's name."""
    device = computer("m1", None)
    device["general"]["extensionAttributes"] = [
        _ea("Anything", "ERROR:oversize:271044"),
    ]
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[device]]), monkeypatch)
    assert records == []
    assert "oversize" in caplog.text
    assert "271044" in caplog.text


def test_a_scan_that_decodes_nothing_says_so_rather_than_reading_as_a_clean_fleet(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Publishing nothing makes "no agents anywhere" and "collection is broken"
    identical in the only output anyone looks at."""
    devices = [[computer("m1", None), computer("m2", "no-cache")]]
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf(devices), monkeypatch)
    assert records == []
    assert "decoded 0 of 2 device(s)" in caplog.text


def _agentless_pages(pages: int) -> list[list[dict[str, Any]]]:
    """A fleet with no discovered agents: Jamf pages on and the connector never yields."""
    return [
        [computer(f"m{p}-{i}", None, ident=p * 10 + i + 1) for i in range(2)]
        for p in range(pages)
    ]


def test_a_stop_check_ends_a_scan_that_never_yields_between_pages(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """What bounds a Test Connection on a fleet with few agents: without the check the
    connector would walk the whole inventory before the caller could stop it."""
    fake = FakeJamf(_agentless_pages(10))
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    asked = {"n": 0}

    def should_stop() -> bool:
        asked["n"] += 1
        return asked["n"] >= 3

    connector = JamfConnector()
    connector.stop_when(should_stop)
    with caplog.at_level(logging.INFO):
        batches = list(connector.scan(FakeConfig(CATALOG), 24, CREDS, FIELDS, LOG))  # type: ignore[arg-type]

    assert batches == []
    # Asked after each device; answered True on the third, the first of page two, so
    # page three was never requested.
    assert asked["n"] == 3
    assert len(fake.gets) == 2
    coverage = connector.device_coverage()
    assert coverage is not None and coverage.devices_read == 3
    assert "stopped early on request after 3 device(s)" in caplog.text


def test_without_a_stop_check_a_scan_reads_the_whole_inventory(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A scheduled scan sets no check and must be unchanged by the option existing."""
    fake = FakeJamf(_agentless_pages(10))
    with caplog.at_level(logging.INFO):
        assert scan(fake, monkeypatch) == []
    # Every page, and the empty one that tells the keyset walk it has reached the end.
    assert len(fake.gets) == 11
    assert "stopped early" not in caplog.text


def test_the_registered_connector_accepts_a_stop_check() -> None:
    from job_executors.discovery_scan import AcceptsStopCheck

    assert isinstance(JamfConnector(), AcceptsStopCheck)


def test_a_fleet_that_really_has_no_agents_is_not_reported_as_broken(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A Mac that scanned and matched nothing DECODED, so the warning must not fire --
    otherwise the signal means nothing the first time it is right."""
    clean = frame([row("app", "com.apple.Safari"), scan_row("apps")])
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[computer("m1", clean)]]), monkeypatch)
    assert records == []
    assert "decoded 0" not in caplog.text


def test_a_mac_that_scanned_and_matched_nothing_yields_no_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """And is NOT logged as unreadable -- it is a real reading that found nothing."""
    payload = frame([row("app", "com.apple.Safari"), scan_row("apps")])
    records = scan(FakeJamf([[computer("m1", payload)]]), monkeypatch)
    assert records == []


def test_a_branch_that_could_not_look_still_reports_the_findings_it_has(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A wedged Docker daemon does not invalidate what the other branches saw."""
    payload = frame(
        [
            row("npm", "@openai/codex"),
            scan_row("packages"),
            scan_row("containers", extra="unhealthy:000"),
        ],
    )
    with caplog.at_level(logging.INFO):
        records = scan(FakeJamf([[computer("m1", payload)]]), monkeypatch)
    assert len(records) == 1
    assert "could not look" in caplog.text
    assert "containers=unhealthy:000" in caplog.text


def test_external_id_uses_the_management_id_not_the_serial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VMs and refurbished units produce empty or duplicate serials, and a churning
    external_id mints duplicate tasks on every scan."""
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    records = scan(FakeJamf([[computer("m1", payload)]]), monkeypatch)
    assert records[0].external_id.startswith("m1:")
    assert "SER" not in records[0].external_id


# --- configuration ----------------------------------------------------------------


@pytest.mark.parametrize("missing", ["base_url", "client_id", "client_secret"])
def test_a_missing_source_field_is_named(missing: str) -> None:
    creds = {k: v for k, v in CREDS.items() if k != missing}
    fields = {k: v for k, v in FIELDS.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        _settings_from(creds, fields)


def test_importing_the_package_registers_the_connector() -> None:
    """The executor resolves a source's vendor against SOURCE_CONNECTORS, so a connector
    nobody imported is a connector that fails its own job as an unsupported vendor."""
    import discovery  # noqa: F401
    from job_executors.discovery_scan import SOURCE_CONNECTORS

    assert "jamf_pro" in SOURCE_CONNECTORS
    # The registry holds factories, so each run gets its own connector rather than sharing
    # one that carries a session and a paging cursor between them.
    assert SOURCE_CONNECTORS["jamf_pro"] is JamfConnector
    assert isinstance(SOURCE_CONNECTORS["jamf_pro"](), JamfConnector)


def test_the_registered_connector_satisfies_the_protocol() -> None:
    """Structural, not nominal: the executor calls .scan(...) with five arguments."""
    import discovery  # noqa: F401
    from job_executors.discovery_scan import SOURCE_CONNECTORS

    connector = SOURCE_CONNECTORS["jamf_pro"]()
    assert callable(getattr(connector, "scan", None))


def test_a_computer_with_no_management_id_is_skipped_not_keyed_blank(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The composite-key trap, in the one place it can still be seen.

    external_id is f"{device_key}:{agent_id}", so a blank device key produces
    ":codex-cli" -- not blank, valid to every downstream guard, and collapsing every
    device with an unreadable id onto a single identity.
    """
    payload = frame([row("npm", "@openai/codex"), scan_row("packages")])
    record = computer("", payload)
    record["general"]["managementId"] = None
    with caplog.at_level(logging.WARNING):
        records = scan(FakeJamf([[record]]), monkeypatch)
    assert records == []
    assert "blank device key" in caplog.text


# --- the creation source, which is what the contract change was for ----------------


def full_payload() -> str:
    return frame(
        [
            row(
                "app",
                "com.anthropic.claudefordesktop",
                ver="1.2.3",
                loc="/Applications/Claude.app",
                perms="tabs,<all_urls>",
            ),
            row("npm", "@openai/codex", ver="0.5.0"),
            scan_row("apps"),
        ],
    )


def test_a_record_carries_the_sensor_that_found_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The whole point of arthur-common#213: before it, everything below was computed
    in the connector and had nowhere to travel."""
    records = scan(FakeJamf([[computer("m1", full_payload())]]), monkeypatch)
    source = records[0].creation_source
    assert source.type == "ENDPOINT"
    assert source.vendor == "jamf_pro"


def test_the_address_names_the_evidence_while_external_id_names_the_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deliberately different keys for different questions.

    external_id is (device, agent) so that uninstalling one of several routes does not
    churn identity and mint a duplicate task. The address is (device, primary route)
    because its job is finding the thing again on the machine -- a bundle id you can
    look up, not a catalog key you cannot.
    """
    records = scan(FakeJamf([[computer("m1", full_payload())]]), monkeypatch)
    codex = next(r for r in records if r.external_id.endswith("codex-cli"))

    assert codex.external_id == "m1:codex-cli"
    assert codex.creation_source.address.instance == "m1"
    assert codex.creation_source.address.resource_kind == "npm"
    assert codex.creation_source.address.resource_id == "@openai/codex"


def test_observations_carry_what_only_the_connector_saw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """install_path, version, permissions and classification come off the payload and
    the catalog; the device fields come off Jamf's own record."""
    catalog = yaml.safe_dump(
        {
            "version": 2,
            "classifications": ["Desktop assistant"],
            "agents": [
                {
                    "id": "claude-desktop",
                    "name": "Claude Desktop",
                    "classification": "Desktop assistant",
                    "platforms": ["darwin"],
                    "bundle_ids": ["com.anthropic.claudefordesktop"],
                },
            ],
        },
    )
    fake = FakeJamf([[computer("m1", full_payload())]])
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    connector = JamfConnector()
    records = [r for b in connector.scan(FakeConfig(catalog), 24, CREDS, FIELDS, LOG) for r in b]  # type: ignore[arg-type]

    obs = records[0].creation_source.observations
    assert obs.install_path == "/Applications/Claude.app"
    assert obs.version == "1.2.3"
    assert obs.permissions == ["tabs", "<all_urls>"]
    assert obs.classification == "Desktop assistant"
    assert obs.host_name == "mac-m1"
    assert obs.os_version == "26.0"
    assert obs.assigned_user == "nori"


def test_a_record_says_it_runs_on_a_managed_mac(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The source is the only thing that knows: a SIEM row can name a laptop too, so
    nothing downstream can infer `endpoint` from the source class."""
    records = scan(FakeJamf([[computer("m1", full_payload())]]), monkeypatch)
    assert {(r.runs_on, r.platform) for r in records} == {
        (RunsOn.ENDPOINT, Platform.DARWIN),
    }


@pytest.mark.parametrize("os_name", ["macOS", "Mac OS X", "OS X", " macos "])
def test_every_name_jamf_has_given_macos_is_darwin(
    os_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    device = computer("m1", full_payload())
    device["operatingSystem"]["name"] = os_name
    records = scan(FakeJamf([[device]]), monkeypatch)
    assert records[0].platform is Platform.DARWIN


@pytest.mark.parametrize("os_name", [None, "", "Plan 9"])
def test_an_os_name_this_does_not_know_leaves_platform_absent(
    os_name: Optional[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absent, not guessed: a wrong OS would file the agent under the wrong filter.
    Where the machine is does not depend on it, so `runs_on` still stands."""
    device = computer("m1", full_payload())
    device["operatingSystem"]["name"] = os_name
    records = scan(FakeJamf([[device]]), monkeypatch)
    assert records[0].platform is None
    assert records[0].runs_on is RunsOn.ENDPOINT


def test_service_names_is_empty_because_a_sweep_sees_installation_not_behaviour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """So the resolver's service-name rung never fires for an endpoint record, which is
    correct rather than a gap: nothing on disk says what a process calls itself."""
    records = scan(FakeJamf([[computer("m1", full_payload())]]), monkeypatch)
    assert records[0].service_names == []


def test_the_record_still_satisfies_the_query_column_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It is a DiscoveryOutputRecord, which is what lets it travel through D-07's
    existing Iterator[Sequence[DiscoveryOutputRecord]] seam unchanged."""
    from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

    records = scan(FakeJamf([[computer("m1", full_payload())]]), monkeypatch)
    assert isinstance(records[0], DiscoveryOutputRecord)
    for column in DiscoveryOutputRecord.required_columns():
        assert getattr(records[0], column) is not None


@pytest.mark.parametrize(
    "kind,ident,loc,ver",
    [
        ("image", "paulgauthier/aider", "0d54037f6c97c85a926ebc", ""),
        ("ilabel", "https://github.com/x/y", "sha256:abc123", ""),
    ],
)
def test_an_opaque_id_is_not_reported_as_an_install_path(
    kind: str,
    ident: str,
    loc: str,
    ver: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`loc` is a filesystem path for most kinds and an image or container id for the
    container ones. Found on a real Mac: aider matched through `images` and reported its
    image sha as install_path -- a path that does not exist anywhere."""
    catalog = yaml.safe_dump(
        {
            "version": 2,
            "classifications": ["Coding agent"],
            "agents": [
                {
                    "id": "aider",
                    "name": "aider",
                    "classification": "Coding agent",
                    "platforms": ["darwin"],
                    "images": ["paulgauthier/aider"],
                    "image_labels": ["https://github.com/x/y"],
                },
            ],
        },
    )
    payload = frame([row(kind, ident, loc=loc, ver=ver), scan_row("containers")])
    fake = FakeJamf([[computer("m1", payload)]])
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    records = [r for b in JamfConnector().scan(FakeConfig(catalog), 24, CREDS, FIELDS, LOG) for r in b]  # type: ignore[arg-type]

    assert records, "the record itself must still be reported"
    assert records[0].creation_source.observations.install_path is None
    # the id is not lost -- it is in the address, where it means what it says
    assert records[0].creation_source.address.resource_id == ident


def test_a_container_state_is_not_reported_as_a_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ver` on a container row is its state. "running" is not a version."""
    catalog = yaml.safe_dump(
        {
            "version": 2,
            "classifications": ["Coding agent"],
            "agents": [
                {
                    "id": "aider",
                    "name": "aider",
                    "classification": "Coding agent",
                    "platforms": ["darwin"],
                    "images": ["paulgauthier/aider"],
                },
            ],
        },
    )
    payload = frame(
        [
            row("container", "paulgauthier/aider:latest", ver="running", loc="c0ffee"),
            scan_row("containers"),
        ],
    )
    fake = FakeJamf([[computer("m1", payload)]])
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    records = [r for b in JamfConnector().scan(FakeConfig(catalog), 24, CREDS, FIELDS, LOG) for r in b]  # type: ignore[arg-type]

    assert records[0].creation_source.observations.version is None


# --- the secret in the token request's body ----------------------------------------


@pytest.mark.parametrize(
    "url",
    ["http://acme.jamfcloud.com", "acme.jamfcloud.com", "ftp://x"],
)
def test_a_non_https_base_url_is_refused(url: str) -> None:
    """client_secret travels in the token request's BODY, so http sends it in cleartext.
    This is the only place it can be refused before it is on the wire."""
    with pytest.raises(ValueError, match="https"):
        _settings_from(CREDS, {"base_url": url})


def test_the_token_request_does_not_follow_redirects() -> None:
    """requests follows redirects by default, and on a 307/308 resends method and body to
    the Location host -- stripping Authorization but not the body, so the secret would go
    wherever the redirect names."""
    seen: dict[str, Any] = {}

    class Recording(FakeJamf):
        def post(self, url: str, **kw: Any) -> FakeResponse:
            seen.update(kw)
            return super().post(url, **kw)

    fake = Recording([[computer("a", None)]])
    list(client_for(fake).devices_since(None))
    assert seen.get("allow_redirects") is False


# --- transport failures, not just statuses ------------------------------------------


@pytest.mark.parametrize("exc", [requests.ConnectionError, requests.Timeout])
def test_a_transport_failure_is_retried_rather_than_ending_the_scan(exc: type) -> None:
    """One reset on page 40 of a hundred-page fleet scan should not end the scan."""
    calls = {"n": 0}

    class Flaky(FakeJamf):
        def get(self, url: str, params: dict[str, Any], **kw: Any) -> FakeResponse:
            calls["n"] += 1
            if calls["n"] == 1:
                raise exc("boom")
            return super().get(url, params, **kw)

    fake = Flaky([[computer("a", None)]])
    assert [d.device_key for d in client_for(fake).devices_since(None)] == ["a"]
    assert calls["n"] > 1, "the failed attempt must have been retried, not propagated"


def test_a_transport_failure_that_never_clears_fails_with_the_cause() -> None:
    class Dead(FakeJamf):
        def get(self, url: str, params: dict[str, Any], **kw: Any) -> FakeResponse:
            raise requests.ConnectionError("no route to host")

    with pytest.raises(JamfError, match="unreachable"):
        list(client_for(Dead([[]])).devices_since(None))


@pytest.mark.parametrize("ver", ["999999999999", "-99999999999999"])
def test_an_out_of_range_scan_timestamp_does_not_end_the_fleet_scan(
    ver: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """datetime.fromtimestamp raises on a `ver` outside the representable range. That
    comes off a device payload, so it must cost that device and no others."""
    payload = frame(
        [row("npm", "@openai/codex"), row("scan", "packages", ver=ver, extra="ok")],
    )
    devices = [
        computer("bad", payload, ident=1),
        computer("good", full_payload(), ident=2),
    ]
    fake = FakeJamf(devices=devices, page_size=5)
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    records = [r for b in JamfConnector().scan(FakeConfig(CATALOG), 0, CREDS, FIELDS, LOG) for r in b]  # type: ignore[arg-type]

    # The bad device falls back to the MDM's own report date, which is the designed
    # behaviour; what matters is that it does not raise and take the rest of the fleet.
    assert any(r.external_id.startswith("good:") for r in records)


def test_the_filter_is_not_percent_encoded_before_requests_encodes_it() -> None:
    """requests encodes the param, so pre-quoting means Jamf decodes once and finds
    `2026-09-22T09%3A00%3A00Z` inside the RSQL instead of a timestamp -- rejected with a
    400, which is not retryable, so every incremental scan would fail.

    Asserted on what reaches the wire rather than on the client's own string, because the
    test fake decoding one extra time is what hid this in the first place.
    """
    import requests as _r

    fake = FakeJamf([[computer("a", None)]])
    list(client_for(fake).devices_since("2026-09-22T09:00:00Z"))
    built = fake.gets[0]["filter"]
    assert "%3A" not in built, "the client must not pre-encode"

    on_wire = _r.Request("GET", "https://x/api", params={"filter": built}).prepare().url
    assert on_wire is not None
    from urllib.parse import unquote as _unq

    assert "2026-09-22T09:00:00Z" in _unq(on_wire.split("filter=")[1])


def test_a_deletion_mid_roster_does_not_skip_the_device_behind_it() -> None:
    """`id` never changes, but an OFFSET over it still slips when a device is deleted:
    every id after it moves down a position and one falls into a page already read."""
    devices = [computer(c, None, ident=i) for i, c in enumerate("abcd", start=1)]

    def delete_after_first_page(fake: "FakeJamf", call: int) -> None:
        if call == 1:
            fake.devices = [d for d in fake.devices if d["id"] != 1]

    fake = FakeJamf(devices=devices, page_size=2, on_page=delete_after_first_page)
    seen = [d.device_key for d in client_for(fake).devices_since(None)]
    assert seen == [
        "a",
        "b",
        "c",
        "d",
    ], "no device behind the deleted one may be skipped"


def test_the_roster_walk_keysets_on_id_rather_than_paging_by_offset() -> None:
    fake = FakeJamf(
        devices=[computer(c, None, ident=i) for i, c in enumerate("abc", start=1)],
        page_size=2,
    )
    list(client_for(fake).devices_since(None))
    assert fake.gets[0].get("filter") is None
    assert fake.gets[1]["filter"].startswith("id=gt=")
    assert all(g["page"] == 0 for g in fake.gets)


def test_the_scan_logs_through_the_logger_it_is_handed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ScopeJobLogExporter is attached to the per-job logger alone, so a connector logging
    to getLogger(__name__) reaches process stdout and never the Platform."""
    job_log = logging.getLogger("a-particular-job-id")
    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    job_log.addHandler(Capture())
    job_log.setLevel(logging.INFO)

    fake = FakeJamf([[computer("m1", "no-cache")]])
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    list(JamfConnector().scan(FakeConfig(CATALOG), 24, CREDS, FIELDS, job_log))  # type: ignore[arg-type]

    assert records, "nothing reached the job logger"
    assert any("no usable payload" in r.getMessage() for r in records)
    assert all(r.name == "a-particular-job-id" for r in records)


def test_base_url_comes_from_the_source_fields_not_the_secrets() -> None:
    """It is not a secret, and taking it from the credentials mapping would register it
    as a scrub target -- striking the host out of the log lines that say which one
    failed."""
    settings = _settings_from(CREDS, FIELDS)
    assert settings.base_url == "https://acme.jamfcloud.com"


def test_base_url_in_the_credentials_is_ignored() -> None:
    """A source that still declares it as a secret does not accidentally keep working:
    the field is read from one place only."""
    with pytest.raises(ValueError, match="base_url"):
        _settings_from({**CREDS, "base_url": "https://sneaky.example"}, {})


# --- device-group scope -----------------------------------------------------------

JAMF_GROUPS = [
    {"id": "1", "name": "All Managed Clients", "smartGroup": True},
    {"id": "7", "name": "Engineering", "smartGroup": True},
    {"id": "8", "name": "Contractors", "smartGroup": False},
    {"id": "9", "name": "Executives", "smartGroup": True},
]


def scan_scoped(
    fake: FakeJamf,
    monkeypatch: pytest.MonkeyPatch,
    include: str = "",
    exclude: str = "",
    connector: Optional[JamfConnector] = None,
) -> list[Any]:
    """A scan whose client is built from the connector's own settings, scope and all.

    `scan` above hands every test the same fixed settings, which would drop the group
    fields on the floor and test nothing.
    """
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: JamfClient(
            dataclasses.replace(s, page_size=2),
            session=fake,  # type: ignore[arg-type]
            sleep=lambda _s: None,
        ),
    )
    fields = {**FIELDS, "include_groups": include, "exclude_groups": exclude}
    connector = connector or JamfConnector()
    return [r for batch in connector.scan(FakeConfig(CATALOG), 24, CREDS, fields, LOG) for r in batch]  # type: ignore[arg-type]


def devices_found(records: list[Any]) -> set[str]:
    return {r.external_id.split(":")[0] for r in records}


def test_group_fields_are_read_from_the_source_fields() -> None:
    settings = _settings_from(
        CREDS,
        {
            **FIELDS,
            "include_groups": "Engineering, Design",
            "exclude_groups": " Executives ",
        },
    )
    assert settings.include_groups == ("Engineering", "Design")
    assert settings.exclude_groups == ("Executives",)
    assert settings.scoped_to_groups
    assert not _settings_from(CREDS, FIELDS).scoped_to_groups


def test_an_excluded_group_keeps_its_macs_out_of_the_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeJamf(
        [
            [
                computer("eng", full_payload(), groups=["1", "7"]),
                computer("exec", full_payload(), groups=["1", "7", "9"]),
            ],
        ],
        groups=JAMF_GROUPS,
    )
    connector = JamfConnector()
    records = scan_scoped(fake, monkeypatch, exclude="Executives", connector=connector)

    assert devices_found(records) == {"eng"}
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (
        coverage.devices_read,
        coverage.devices_in_scope,
        coverage.devices_excluded,
    ) == (2, 1, 1)
    assert coverage.excluded_by_group == {"Executives": 1}


def test_include_groups_limit_the_scan_to_their_members(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeJamf(
        [
            [
                computer("eng", full_payload(), groups=["1", "7"]),
                computer("sales", full_payload(), groups=["1"]),
            ],
        ],
        groups=JAMF_GROUPS,
    )
    connector = JamfConnector()
    records = scan_scoped(fake, monkeypatch, include="Engineering", connector=connector)

    assert devices_found(records) == {"eng"}
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_outside_included_groups == 1
    assert coverage.included_by_group == {"Engineering": 1}


def test_an_out_of_scope_mac_is_dropped_before_its_payload_is_decoded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nothing from an excluded Mac is decoded, logged or published -- it contributes
    counts and nothing else."""
    decoded: list[str] = []

    def recording(device: Any, *args: Any) -> Any:
        decoded.append(device.device_key)
        return records_for(device, *args)

    monkeypatch.setattr("discovery.endpoint.jamf.connector.records_for", recording)
    fake = FakeJamf(
        [
            [
                computer("eng", full_payload(), groups=["7"]),
                computer("exec", "not a payload", groups=["9"]),
            ],
        ],
        groups=JAMF_GROUPS,
    )
    connector = JamfConnector()
    scan_scoped(fake, monkeypatch, exclude="Executives", connector=connector)

    assert decoded == ["eng"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_unreadable == 0, "an excluded Mac is not an unreadable one"


def test_group_memberships_are_asked_for_only_when_the_source_is_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unscoped source asks Jamf for exactly what it did before, and needs no group
    privilege."""
    unscoped = FakeJamf([[computer("m1", full_payload())]])
    scan_scoped(unscoped, monkeypatch)
    assert "GROUP_MEMBERSHIPS" not in unscoped.gets[0]["section"]
    assert unscoped.group_calls == 0

    scoped = FakeJamf(
        [[computer("m1", full_payload(), groups=["1"])]],
        groups=JAMF_GROUPS,
    )
    scan_scoped(scoped, monkeypatch, exclude="Contractors")
    assert "GROUP_MEMBERSHIPS" in scoped.gets[0]["section"]
    assert scoped.group_calls == 1


def test_a_group_the_tenant_does_not_have_fails_before_any_mac_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A renamed or misspelled exclude group must not quietly scan the Macs it was
    meant to leave out."""
    fake = FakeJamf(
        [[computer("exec", full_payload(), groups=["9"])]],
        groups=JAMF_GROUPS,
    )
    connector = JamfConnector()
    with pytest.raises(DeviceGroupError, match="'Execs' not found"):
        scan_scoped(fake, monkeypatch, exclude="Execs", connector=connector)
    assert fake.gets == [], "no inventory page was requested"
    assert connector.device_coverage() is None


def test_a_missing_group_privilege_names_the_privileges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeJamf([[computer("m1", full_payload())]], groups_status=403)
    with pytest.raises(JamfError, match="Read Smart Computer Groups and Read Static"):
        scan_scoped(fake, monkeypatch, exclude="Executives")


def test_the_scope_and_its_counts_reach_the_job_log(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeJamf(
        [
            [
                computer("m1", full_payload(), groups=["1"]),
                computer("m2", full_payload(), groups=["8"]),
            ],
        ],
        groups=JAMF_GROUPS,
    )
    with caplog.at_level(logging.INFO):
        scan_scoped(fake, monkeypatch, exclude="Contractors, Executives")
    assert "scope: exclude Contractors, Executives" in caplog.text
    assert "kept 1 of 2 device(s); excluded 1 (Contractors: 1, Executives: 0)" in (
        caplog.text
    )


def test_a_scope_that_leaves_every_mac_out_says_so(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """It publishes the same nothing as a fleet without agents, so it is called out."""
    fake = FakeJamf(
        [[computer("m1", full_payload(), groups=["8"])]],
        groups=JAMF_GROUPS,
    )
    with caplog.at_level(logging.WARNING):
        scan_scoped(fake, monkeypatch, exclude="Contractors")
    assert "left all 1 device(s) it read out of scope" in caplog.text


def test_an_unscoped_scan_still_reports_its_denominator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeJamf(
        [
            [
                computer("m1", full_payload()),
                computer("m2", "not a payload"),
            ],
        ],
    )
    connector = JamfConnector()
    scan_scoped(fake, monkeypatch, connector=connector)
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (
        coverage.devices_read,
        coverage.devices_in_scope,
        coverage.devices_decoded,
        coverage.devices_unreadable,
        coverage.devices_excluded,
    ) == (2, 2, 1, 1, 0)
    assert coverage.excluded_by_group == {}


def test_unreadable_macs_are_counted_by_why(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each asks for a different fix, so the run says which, not only how many."""
    other = frame([row("npm", "@openai/codex", ver="0.6.0"), scan_row("apps")])
    fake = FakeJamf(
        [
            [
                computer("read", full_payload()),
                computer("silent", None),
                computer("stale", EnvelopeOutcome.NO_CACHE.value),
            ],
            [
                computer("huge", "ERROR:oversize:300000"),
                computer("garbled", "arthur1.not-base64!"),
                computer(
                    "twice",
                    full_payload(),
                    extra_attributes=[{"name": "Second Copy", "values": [other]}],
                ),
            ],
        ],
    )
    connector = JamfConnector()
    scan_scoped(fake, monkeypatch, connector=connector)
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (coverage.devices_decoded, coverage.devices_unreadable) == (1, 5)
    assert coverage.unreadable_by_reason == {
        "never-reported": 1,
        "no-cache": 1,
        "oversize": 1,
        "malformed": 1,
        "conflicting-attributes": 1,
    }


# --- what is never collected ----------------------------------------------------------
#
# D-19's never-collected list: prompt and response contents, file contents, keystrokes
# or screen data, personal browsing history. Enforced in three places, each with a test
# here: the sections the connector asks Jamf for, the fields it keeps from a device
# record, and the six columns it accepts from the collector. The record schema is the
# fourth: it has no field that could carry any of them.

PERSONAL = {
    "email": "nori@example.com",
    "phone": "+1 555 0100",
    "real name": "Nori Tatsumi",
    "ip address": "10.1.2.3",
    "mac address": "aa:bb:cc:dd:ee:ff",
    "an unrelated extension attribute": "PERSONAL NOTES ABOUT THIS USER",
    "prompt text": "SECRET PROMPT TEXT",
    "browsing history": "https://intranet.example.com/hr/review",
}


def prying_computer(mid: str, value: str) -> dict[str, Any]:
    """A Jamf record padded with what the inventory API can say about a person and a
    machine that this source has no business carrying."""
    record = computer(
        mid,
        value,
        extra_attributes=[_ea("Notes", PERSONAL["an unrelated extension attribute"])],
    )
    record["general"].update(
        {
            "lastIpAddress": PERSONAL["ip address"],
            "lastReportedIp": PERSONAL["ip address"],
        },
    )
    record["hardware"]["macAddress"] = PERSONAL["mac address"]
    record["userAndLocation"].update(
        {
            "realname": PERSONAL["real name"],
            "email": PERSONAL["email"],
            "phone": PERSONAL["phone"],
            "position": "Engineer",
        },
    )
    record["localUserAccounts"] = [
        {
            "username": "nori",
            "fullName": PERSONAL["real name"],
            "homeDirectory": "/Users/nori",
        },
    ]
    record["applications"] = [{"name": "Safari", "path": "/Applications/Safari.app"}]
    record["attachments"] = [{"name": "hr-review.pdf"}]
    return record


def test_the_connector_asks_jamf_only_for_the_sections_it_reads() -> None:
    """What is never requested cannot be collected. Applications, local user accounts,
    attachments, certificates and the rest of the inventory are not on the list; a scoped
    source adds only the group memberships it needs to apply its scope."""
    fake = FakeJamf([[computer("m1", full_payload())]])
    list(client_for(fake).devices_since(None))
    assert set(fake.gets[0]["section"]) == {
        "GENERAL",
        "HARDWARE",
        "OPERATING_SYSTEM",
        "USER_AND_LOCATION",
        "EXTENSION_ATTRIBUTES",
    }


def test_a_device_record_keeps_nothing_the_observations_do_not_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Jamf's record says far more about a machine and its user than this source
    reports. The connector copies the fields `AgentObservations` names and drops the
    record; nothing else survives to be serialized."""
    records = scan(FakeJamf([[prying_computer("m1", full_payload())]]), monkeypatch)
    assert records, "the padding must not make the device unreadable"

    wire = json.dumps([r.model_dump(mode="json") for r in records])
    for what, value in PERSONAL.items():
        assert value not in wire, f"{what} reached the record"
    assert '"assigned_user": "nori"' in wire, "the allow-listed user is still there"


def test_a_row_with_more_than_the_six_columns_is_refused_not_forwarded(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A collector that starts writing what it read -- a prompt, a file -- fails the
    device rather than shipping the extra column. The contract is the privacy boundary,
    and the warning names the column, never its value."""
    rows = [row("npm", "@openai/codex", ver="0.5.0"), scan_row("packages")]
    rows[0]["contents"] = PERSONAL["prompt text"]
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(FakeJamf([[computer("m1", frame(rows))]]), monkeypatch)

    assert records == []
    assert "unexpected ['contents']" in caplog.text
    assert PERSONAL["prompt text"] not in caplog.text


def test_the_extra_column_never_reaches_a_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`extra` means something different per kind and is the one column with room for
    free text. Nothing reads it into a record: it stays on the wire."""
    rows = [
        row("npm", "@openai/codex", ver="0.5.0", extra=PERSONAL["prompt text"]),
        scan_row("packages"),
    ]
    records = scan(FakeJamf([[computer("m1", frame(rows))]]), monkeypatch)
    assert len(records) == 1
    assert PERSONAL["prompt text"] not in json.dumps(records[0].model_dump(mode="json"))


def test_the_record_schema_has_no_field_for_what_is_never_collected() -> None:
    """The allow-list, as the shape of the record itself: a field that is not here cannot
    be filled by mistake. Adding one is a privacy review, not a refactor."""
    assert set(EndpointAgentCreationSource.model_fields) == {
        "type",
        "vendor",
        "address",
        "observations",
    }
    assert set(SourceAddress.model_fields) == {
        "instance",
        "scope",
        "resource_kind",
        "resource_id",
        "query",
    }
    assert set(AgentObservations.model_fields) == {
        "install_path",
        "version",
        "host_name",
        "host_group",
        "os_version",
        "assigned_user",
        "permissions",
        "service_names",
        "classification",
    }


# --- a base_url that is https but not a usable address ------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://acme.jamfcloud.com:abc",
        "https://acme.jamfcloud.com:99999",
        "https://[acme.jamfcloud.com",
        "https://",
        "https://acme jamfcloud.com",
        "https://acme.jamfcloud.com\u200b",
        "https://.acme.jamfcloud.com",
        "https://*.jamfcloud.com",
        "https://acme.jamfcloud.com%",
    ],
)
def test_a_malformed_base_url_is_not_configured(url: str) -> None:
    """https passes the scheme check, but requests cannot send to any of these: it raises
    InvalidURL, a ValueError the client's transport handling does not catch, so a
    scheduled scan read it as the vendor failing."""
    with pytest.raises(DiscoveryConfigurationError) as caught:
        _settings_from(CREDS, {"base_url": url})

    assert failure_code(caught.value) == DiscoveryErrorCode.NOT_CONFIGURED
    assert "base_url" in str(caught.value)
    # Test Connection walks __cause__/__context__; the parse error must not ride along.
    assert caught.value.__cause__ is None and caught.value.__context__ is None


@pytest.mark.parametrize(
    "url",
    [
        "https://user:hunter2@acme.jamfcloud.com",
        "https://user:hunter2@acme.jamfcloud.com:abc",
    ],
)
def test_a_base_url_with_credentials_is_refused_without_repeating_them(
    url: str,
) -> None:
    """requests turns URL userinfo into a Basic header that replaces the Bearer token, so
    every call would 401. base_url is outside the scrub set, so the message must not
    repeat it."""
    with pytest.raises(DiscoveryConfigurationError) as caught:
        _settings_from(CREDS, {"base_url": url})

    assert failure_code(caught.value) == DiscoveryErrorCode.NOT_CONFIGURED
    assert "hunter2" not in str(caught.value)
    assert "user:" not in str(caught.value)


@pytest.fixture
def lookups(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Hosts the real requests/urllib3 stack tried to resolve, i.e. tried to reach.

    Each lookup is refused, so nothing leaves the machine either way."""
    seen: list[str] = []

    def refuse(host: str, *a: Any, **kw: Any) -> Any:
        seen.append(host)
        raise OSError("this test resolves nothing")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    return seen


def _session(trust_env: bool = False) -> requests.Session:
    """A real Session. Without the environment by default, so an HTTPS_PROXY on the
    machine running the tests does not decide which host gets looked up."""
    session = requests.Session()
    session.trust_env = trust_env
    return session


def _scan_through_requests(
    url: str,
    monkeypatch: pytest.MonkeyPatch,
    session: Optional[requests.Session] = None,
) -> BaseException:
    """Run a scan with the real JamfClient and a real requests.Session."""
    http = session or _session()
    monkeypatch.setattr(
        "discovery.endpoint.jamf.connector.JamfClient",
        lambda s, logger=None: JamfClient(
            s, logger=logger, session=http, sleep=lambda _s: None
        ),
    )
    with pytest.raises(Exception) as caught:
        list(
            JamfConnector().scan(
                FakeConfig(CATALOG), 24, CREDS, {"base_url": url}, LOG  # type: ignore[arg-type]
            ),
        )
    return caught.value


def test_a_host_urllib3_refuses_at_connect_is_not_configured_and_never_reached(
    lookups: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty label passes requests' URL preparation; urllib3 refuses it only when it
    opens the connection, with LocationParseError. That is where the client classifies
    it, before any lookup of the host."""
    exc = _scan_through_requests("https://acme..jamfcloud.com", monkeypatch)

    assert failure_code(exc) == DiscoveryErrorCode.NOT_CONFIGURED
    assert exc.__cause__ is None and exc.__context__ is None
    assert "acme" not in str(exc)
    assert lookups == []


def test_a_well_formed_base_url_does_reach_the_network(
    lookups: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The control for the test above: the same path with a valid host does try to
    resolve it, so an empty `lookups` there means the request was stopped, not that
    lookups go unrecorded."""
    exc = _scan_through_requests("https://acme.jamfcloud.com", monkeypatch)

    assert "acme.jamfcloud.com" in lookups
    assert failure_code(exc) != DiscoveryErrorCode.NOT_CONFIGURED


def test_a_host_urllib3_refuses_at_connect_is_caught_where_the_client_sends(
    lookups: list[str],
) -> None:
    """The client's own check, behind the up-front one: if an address that urllib3
    refuses ever reaches a send, it is still the source's configuration."""
    with pytest.raises(DiscoveryConfigurationError) as caught:
        JamfClient._send(
            _session().post, "https://acme..jamfcloud.com/api/oauth/token", timeout=1
        )

    assert failure_code(caught.value) == DiscoveryErrorCode.NOT_CONFIGURED
    assert caught.value.__cause__ is None and caught.value.__context__ is None
    assert lookups == []


@pytest.mark.parametrize(
    "proxy",
    ["http://proxy.internal:abc", "http://", "http://proxy..internal:3128"],
)
def test_a_malformed_proxy_is_not_blamed_on_a_valid_base_url(
    proxy: str,
    lookups: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """requests raises the same InvalidURL / LocationParseError for a bad HTTPS_PROXY as
    for a bad base_url. The proxy is the engine's environment, not the source's settings,
    so it must not read as the customer's base_url being wrong."""
    for name in ("NO_PROXY", "no_proxy", "https_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HTTPS_PROXY", proxy)

    exc = _scan_through_requests(
        "https://acme.jamfcloud.com", monkeypatch, _session(trust_env=True)
    )

    assert failure_code(exc) != DiscoveryErrorCode.NOT_CONFIGURED


class _RedirectsToNowhere(requests.adapters.BaseAdapter):
    """Plays the configured host: mints a token, then answers every GET with a redirect
    to an address urllib3 refuses. requests sends a redirect target without preparing it
    again, so that request goes to a real HTTPAdapter, which is where it fails."""

    HOME = "acme.jamfcloud.com"

    def __init__(self) -> None:
        super().__init__()
        self._real = requests.adapters.HTTPAdapter()

    def send(self, request: requests.PreparedRequest, **kw: Any) -> requests.Response:
        if urlsplit(str(request.url)).hostname != self.HOME:
            return self._real.send(request, **kw)
        resp = requests.Response()
        resp.request, resp.url = request, str(request.url)
        resp._content_consumed = True
        if request.method == "POST":
            resp.status_code = 200
            resp._content = json.dumps(
                {"access_token": "t", "expires_in": 600}
            ).encode()
        else:
            resp.status_code = 302
            resp._content = b""
            resp.headers["Location"] = "https://acme..jamfcloud.com/next"
        return resp

    def close(self) -> None:
        self._real.close()


def test_a_bad_redirect_target_is_not_blamed_on_a_valid_base_url(
    lookups: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The server answered, at the configured address; where it then pointed is not
    something the source's settings can fix."""
    session = _session()
    session.mount("https://", _RedirectsToNowhere())

    exc = _scan_through_requests("https://acme.jamfcloud.com", monkeypatch, session)

    assert isinstance(exc, LocationValueError), exc
    assert failure_code(exc) != DiscoveryErrorCode.NOT_CONFIGURED
    assert lookups == []


def test_a_well_formed_base_url_with_a_port_is_accepted() -> None:
    settings = _settings_from(CREDS, {"base_url": "https://acme.jamfcloud.com:8443/"})
    assert settings.base_url == "https://acme.jamfcloud.com:8443/"
