"""The Jamf client and scanner, against a fake Jamf.

The paging test is the one that matters most. `general.reportDate` is assigned at
check-in, so records shift between pages while a scan is reading them -- and the failure
mode is silent: the device is not seen again, and the fleet quietly shrinks. UP-4893 makes
a mid-pagination shift an acceptance criterion for exactly that reason.
"""

import base64
import gzip
import io
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import unquote

import pytest
import requests
import yaml

from discovery.endpoint.jamf.client import JamfClient, JamfError, JamfSettings
from discovery.endpoint.jamf.scanner import JamfScanner, _settings_from

SCAN_AT = 1790100381
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
CREDS = {
    "base_url": "https://acme.jamfcloud.com",
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


def computer(
    mid: str,
    value: Optional[str],
    report_date: str = "2026-09-22T10:00:00Z",
    ident: int = 0,
) -> dict[str, Any]:
    return {
        "id": ident or (abs(hash(mid)) % 100000),
        "general": {
            "managementId": mid,
            "name": f"mac-{mid}",
            "reportDate": report_date,
            "extensionAttributes": [
                {
                    "name": "AI Inventory",
                    "values": [value] if value is not None else [],
                },
            ],
        },
        "operatingSystem": {"version": "26.0"},
        "userAndLocation": {"username": "nori"},
        "hardware": {"serialNumber": f"SER{mid}"},
    }


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
        if where is None:  # full enumeration: offset over id
            rows = sorted(self.devices, key=lambda d: int(d["id"]))
            start = params["page"] * self.page_size
            results = rows[start : start + self.page_size]
        else:
            m = re.search(r'reportDate=gt="([^"]+)"', where)
            tie = re.search(r"id=gt=(\d+)", where)
            cursor = (
                (unquote(m.group(1)), int(tie.group(1)) if tie else None) if m else None
            )
            results = self._after(cursor)[: self.page_size]

        self._calls += 1
        if self.on_page:
            self.on_page(self, self._calls)
        return FakeResponse(200, {"totalCount": len(self.devices), "results": results})


def client_for(fake: FakeJamf) -> JamfClient:
    return JamfClient(
        JamfSettings(**CREDS, page_size=2),  # type: ignore[arg-type]
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


# --- the scanner ------------------------------------------------------------------


class FakeConfig:
    def __init__(self, query: Optional[str]) -> None:
        self.query = query
        self.vendor = "jamf_pro"
        self.name = "acme jamf"


def scan(fake: FakeJamf, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    monkeypatch.setattr(
        "discovery.endpoint.jamf.scanner.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    scanner = JamfScanner(logger=logging.getLogger("t"))
    return [r for batch in scanner.scan(FakeConfig(CATALOG), 24, CREDS) for r in batch]  # type: ignore[arg-type]


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
    assert len(records) == 1, "two routes, one agent, one finding"
    assert records[0].external_id == "m1:codex-cli"
    assert records[0].name == "Codex CLI"


def test_last_seen_is_the_scan_timestamp_not_the_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The payload dates itself. Using the poll time would date every finding to now."""
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
    with pytest.raises(ValueError, match=missing):
        _settings_from(creds)


def test_importing_the_package_registers_the_connector() -> None:
    """The executor resolves a source's vendor against SOURCE_SCANNERS, so a connector
    nobody imported is a connector that fails its own job as an unsupported vendor."""
    import discovery  # noqa: F401
    from job_executors.discovery_scan import SOURCE_SCANNERS

    assert "jamf_pro" in SOURCE_SCANNERS
    # The registry holds factories, so each run gets its own scanner rather than sharing
    # one that carries a session and a paging cursor between them.
    assert SOURCE_SCANNERS["jamf_pro"] is JamfScanner
    assert isinstance(SOURCE_SCANNERS["jamf_pro"](), JamfScanner)


def test_the_registered_scanner_satisfies_the_protocol() -> None:
    """Structural, not nominal: the executor calls .scan(config, lookback, credentials)."""
    import discovery  # noqa: F401
    from job_executors.discovery_scan import SOURCE_SCANNERS

    scanner = SOURCE_SCANNERS["jamf_pro"]()
    assert callable(getattr(scanner, "scan", None))


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
        "discovery.endpoint.jamf.scanner.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    scanner = JamfScanner(logger=logging.getLogger("t"))
    records = [r for b in scanner.scan(FakeConfig(catalog), 24, CREDS) for r in b]  # type: ignore[arg-type]

    obs = records[0].creation_source.observations
    assert obs.install_path == "/Applications/Claude.app"
    assert obs.version == "1.2.3"
    assert obs.permissions == ["tabs", "<all_urls>"]
    assert obs.classification == "Desktop assistant"
    assert obs.host_name == "mac-m1"
    assert obs.os_version == "26.0"
    assert obs.assigned_user == "nori"


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
        "discovery.endpoint.jamf.scanner.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    records = [r for b in JamfScanner().scan(FakeConfig(catalog), 24, CREDS) for r in b]  # type: ignore[arg-type]

    assert records, "the finding itself must still be reported"
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
        "discovery.endpoint.jamf.scanner.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    records = [r for b in JamfScanner().scan(FakeConfig(catalog), 24, CREDS) for r in b]  # type: ignore[arg-type]

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
        _settings_from({**CREDS, "base_url": url})


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
        "discovery.endpoint.jamf.scanner.JamfClient",
        lambda s, logger=None: client_for(fake),
    )
    records = [r for b in JamfScanner().scan(FakeConfig(CATALOG), 0, CREDS) for r in b]  # type: ignore[arg-type]

    # The bad device falls back to the MDM's own report date, which is the designed
    # behaviour; what matters is that it does not raise and take the rest of the fleet.
    assert any(r.external_id.startswith("good:") for r in records)
