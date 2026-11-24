"""The GravityZone client and connector, against a fake Control Center.

Built from GravityZone's public API reference, not from a tenant: the response shapes of
`startCommandExecutionOnEndpoint` and `getInvestigationFileUrl` and the output archive's
format are unverified, so the fake serves the forms the client accepts, and the tests
that matter most are the ones that do not depend on them -- an endpoint that cannot
answer is a coverage gap and never a failed scan, the command is a constant, and the key
goes nowhere but the access URL's host.
"""

import base64
import gzip
import io
import json
import logging
import tarfile
import zipfile
from typing import Any, Optional

import pytest
import requests
from arthur_common.models.agent_governance_schemas import (
    EndpointAgentCreationSource,
    Platform,
    RunsOn,
)

from discovery.endpoint.gravityzone import connector as gz
from discovery.endpoint.gravityzone.client import (
    TIMEOUT,
    GravityZoneClient,
    GravityZoneError,
    GravityZoneSettings,
    output_texts,
)
from discovery.endpoint.gravityzone.connector import (
    COMMAND,
    INVENTORY_PATH,
    GravityZoneConnector,
    _settings_from,
    command_value,
)
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)
from tests.fakes.catalog import agent, document
from tests.fakes.records import agent_records

SCAN_AT = 1790100381
LOG = logging.getLogger("discovery-test")
API_KEY = "gz-key-do-not-log"
ACCESS_URL = "https://cloudgz.gravityzone.bitdefender.com/api"
FIELDS = {"access_url": ACCESS_URL}
CREDS = {"api_key": API_KEY}
CATALOG = document(
    agent(
        "codex-cli",
        "Codex CLI",
        "Coding agent",
        npm=["@openai/codex"],
        binaries=["~/.local/bin/codex"],
    ),
)
RECENT = "2026-11-24T09:00:00"


def frame(rows: list[dict[str, str]]) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gzf:
        gzf.write(json.dumps(rows).encode())
    return "arthur1." + base64.b64encode(buf.getvalue()).decode()


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


CODEX = frame(
    [
        row("npm", "@openai/codex"),
        row("scan", "packages", ver=str(SCAN_AT), extra="ok"),
    ],
)


def printed(value: str) -> bytes:
    """What COMMAND prints, as a shell would, when the file holds `value`."""
    return f"ARTHUR-BEGIN\n{value}\nARTHUR-END\n".encode()


def zipped(text: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("output/command.log", text)
    return buf.getvalue()


def endpoint(
    ident: str,
    os_name: str = "macOS Sonoma",
    state: Optional[int] = 1,
    last_seen: Optional[str] = None,
) -> dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "id": ident,
        "name": f"host-{ident}",
        "operatingSystem": os_name,
        "state": state,
        "lastSeen": last_seen
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "group": {"id": "g1", "name": "Engineering"},
    }


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
        raw: Optional[bytes] = None,
    ) -> None:
        self.status_code, self._body = status, body
        self.headers = headers or {}
        self._raw = raw

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("not json")
        return self._body

    def iter_content(self, size: int) -> Any:
        data = self._raw or b""
        for i in range(0, len(data), size):
            yield data[i : i + size]


class FakeGravityZone:
    """A Control Center that answers the five methods the connector calls.

    `outputs[id]` is what that endpoint's command printed (bytes, served as a zip unless
    already packed), or a status word: "failed", "pending" (never finishes), or an int
    HTTP status for the start call to answer with.
    """

    def __init__(
        self,
        endpoints: list[dict[str, Any]],
        outputs: Optional[dict[str, Any]] = None,
        per_page: int = 1000,
        enabled_apis: Optional[list[str]] = None,
        statuses: Optional[dict[str, list[int]]] = None,
        download_host: str = "cloudgz.gravityzone.bitdefender.com",
    ) -> None:
        self.endpoints = endpoints
        self.outputs = outputs or {}
        self.per_page = per_page
        self.enabled_apis = enabled_apis
        self.statuses = statuses or {}
        self.download_host = download_host
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.posts: list[dict[str, Any]] = []
        self.downloads: list[dict[str, Any]] = []

    def post(self, url: str, **kw: Any) -> FakeResponse:
        self.posts.append({"url": url, **kw})
        body = kw["json"]
        method, params = body["method"], body["params"]
        self.calls.append((method, params))
        queued = self.statuses.get(method)
        if queued:
            status = queued.pop(0)
            if status != 200:
                return FakeResponse(
                    status, {"error": {"code": -1}}, {"Retry-After": "0"}
                )
        if method == "getApiKeyDetails":
            if self.enabled_apis is None:
                return FakeResponse(200, {"error": {"code": -32601}})
            return FakeResponse(200, {"result": {"enabledApis": self.enabled_apis}})
        if method == "getEndpointsList":
            page = params["page"]
            start = (page - 1) * self.per_page
            items = self.endpoints[start : start + self.per_page]
            more = start + self.per_page < len(self.endpoints)
            return FakeResponse(
                200,
                {"result": {"items": items, "page": page, "hasMoreRecords": more}},
            )
        if method == "getManagedEndpointDetails":
            found = next(e for e in self.endpoints if e["id"] == params["endpointId"])
            return FakeResponse(200, {"result": found})
        if method == "startCommandExecutionOnEndpoint":
            out = self.outputs.get(params["targetId"])
            if isinstance(out, int):
                return FakeResponse(out, {"error": {"code": -1}})
            return FakeResponse(
                200, {"result": {"activityId": f"act-{params['targetId']}"}}
            )
        if method == "getInvestigationFileUrl":
            target = params["targetId"]
            out = self.outputs.get(target)
            if out == "failed":
                return FakeResponse(200, {"result": {"status": "failed"}})
            if out == "pending" or out is None:
                return FakeResponse(200, {"result": {"status": "pending"}})
            return FakeResponse(
                200,
                {
                    "result": {
                        "status": "success",
                        "url": f"https://{self.download_host}/files/{target}.zip",
                    },
                },
            )
        raise AssertionError(f"unexpected method {method}")

    def get(self, url: str, **kw: Any) -> FakeResponse:
        self.downloads.append({"url": url, **kw})
        target = url.rsplit("/", 1)[1].split(".")[0]
        out = self.outputs[target]
        if isinstance(out, str):
            out = printed(out)
        if not (zipfile.is_zipfile(io.BytesIO(out)) or out[:2] == b"\x1f\x8b"):
            out = zipped(out)
        return FakeResponse(200, raw=out)

    def sent(self, method: str) -> list[dict[str, Any]]:
        return [params for name, params in self.calls if name == method]


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeConfig:
    def __init__(self, query: Optional[str] = CATALOG) -> None:
        self.query = query
        self.vendor = "bitdefender_gravityzone"
        self.name = "acme gravityzone"


def connector_for(
    fake: FakeGravityZone, clock: Optional[FakeClock] = None
) -> GravityZoneConnector:
    clock = clock or FakeClock()
    return GravityZoneConnector(
        client_factory=lambda settings, log: GravityZoneClient(
            settings,
            logger=log,
            session=fake,  # type: ignore[arg-type]
            sleep=clock.sleep,
            clock=clock,
        ),
        sleep=clock.sleep,
        clock=clock,
    )


def scan_all(
    fake: FakeGravityZone,
    lookback_hours: int = 24,
    connector: Optional[GravityZoneConnector] = None,
) -> list[Any]:
    connector = connector or connector_for(fake)
    return [
        record
        for batch in connector.scan(FakeConfig(), lookback_hours, CREDS, FIELDS, LOG)  # type: ignore[arg-type]
        for record in batch
    ]


# --- registration ---------------------------------------------------------------


def test_the_connector_is_registered_and_its_records_are_corroborated() -> None:
    from discovery import corroborating_vendors, source_connectors

    connectors = source_connectors()
    assert connectors["bitdefender_gravityzone"] is GravityZoneConnector
    assert "bitdefender_gravityzone" in corroborating_vendors()
    assert GravityZoneConnector.SENSITIVE_FIELDS == frozenset({"api_key"})


def test_the_connector_reports_coverage_and_takes_a_stop_check() -> None:
    from job_executors.discovery_scan import AcceptsStopCheck, ReportsDeviceCoverage

    assert isinstance(GravityZoneConnector(), AcceptsStopCheck)
    assert isinstance(GravityZoneConnector(), ReportsDeviceCoverage)


# --- the command ----------------------------------------------------------------


def test_the_command_only_reads_the_collector_file_and_fits_the_cap() -> None:
    """It runs as root on every endpoint, so it is a constant: read one file, print it."""
    assert len(COMMAND) <= 10_000
    assert f"cat {INVENTORY_PATH}" in COMMAND
    for verb in ("curl", "wget", "rm ", "bash -c", "sh -c", ">"):
        assert verb not in COMMAND.replace("2>/dev/null", "")


def test_the_markers_never_appear_literally_in_the_command() -> None:
    """If the output echoes the command line, the value is still found only once."""
    assert "ARTHUR-BEGIN" not in COMMAND
    assert "ARTHUR-END" not in COMMAND
    echoed = f"$ {COMMAND}\n".encode() + printed(CODEX)
    assert command_value(list(output_texts(echoed))) == CODEX


def test_no_source_field_reaches_the_command() -> None:
    fake = FakeGravityZone([endpoint("e1")], {"e1": CODEX})
    scan_all(fake)
    [sent] = fake.sent("startCommandExecutionOnEndpoint")
    assert sent == {"targetId": "e1", "command": COMMAND}


@pytest.mark.parametrize(
    "pack",
    [
        pytest.param(zipped, id="zip"),
        pytest.param(lambda t: gzip.compress(t), id="gzip"),
        pytest.param(lambda t: t, id="plain"),
        pytest.param(
            lambda t: _tar(t),
            id="tar.gz",
        ),
    ],
)
def test_the_output_is_found_in_any_archive_form(pack: Any) -> None:
    assert command_value(list(output_texts(pack(printed(CODEX))))) == CODEX


def _tar(text: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as archive:
        info = tarfile.TarInfo("command.log")
        info.size = len(text)
        archive.addfile(info, io.BytesIO(text))
    return buf.getvalue()


# --- records --------------------------------------------------------------------


def test_an_online_mac_yields_its_agent_record_through_the_shared_record_path() -> None:
    fake = FakeGravityZone([endpoint("e1")], {"e1": CODEX})
    connector = connector_for(fake)
    records = agent_records([scan_all(fake, connector=connector)])

    [record] = records
    assert record.external_id.startswith("e1:")
    source = record.creation_source
    assert isinstance(source, EndpointAgentCreationSource)
    assert source.vendor == "bitdefender_gravityzone"
    assert source.address.instance == "e1"
    assert record.runs_on is RunsOn.ENDPOINT
    assert record.platform is Platform.DARWIN
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (coverage.devices_read, coverage.devices_decoded) == (1, 1)


def test_a_linux_endpoint_is_asked_too() -> None:
    fake = FakeGravityZone([endpoint("e1", "Ubuntu 24.04 LTS")], {"e1": CODEX})
    [record] = agent_records([scan_all(fake)])
    assert record.platform is Platform.LINUX


def test_a_malformed_value_is_counted_and_the_scan_goes_on() -> None:
    fake = FakeGravityZone(
        [endpoint("bad"), endpoint("good")],
        {"bad": "arthur1.not-base64!", "good": CODEX},
    )
    connector = connector_for(fake)
    records = agent_records([scan_all(fake, connector=connector)])
    assert [r.external_id.split(":")[0] for r in records] == ["good"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"malformed": 1}


def test_a_missing_collector_file_reads_as_no_cache() -> None:
    fake = FakeGravityZone([endpoint("e1")], {"e1": "no-cache"})
    connector = connector_for(fake)
    assert scan_all(fake, connector=connector) == []
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"no-cache": 1}


# --- coverage gaps --------------------------------------------------------------


def test_offline_windows_and_stale_endpoints_are_gaps_and_get_no_command() -> None:
    fake = FakeGravityZone(
        [
            endpoint("off", state=2),
            endpoint("win", "Windows 11 Enterprise"),
            endpoint("old", last_seen="2026-01-01T00:00:00"),
            endpoint("ok"),
        ],
        {"ok": CODEX},
    )
    connector = connector_for(fake)
    scan_all(fake, lookback_hours=24, connector=connector)

    assert [p["targetId"] for p in fake.sent("startCommandExecutionOnEndpoint")] == [
        "ok"
    ]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {
        "offline": 1,
        "unsupported-platform": 1,
        "not-seen-in-window": 1,
    }
    listed = {d.device_key: d.reason for d in coverage.unreadable_devices}
    assert listed == {
        "off": "offline",
        "win": "unsupported-platform",
        "old": "not-seen-in-window",
    }


def test_a_lookback_of_zero_asks_every_endpoint_however_long_ago_it_was_seen() -> None:
    fake = FakeGravityZone(
        [endpoint("old", last_seen="2026-01-01T00:00:00")],
        {"old": CODEX},
    )
    scan_all(fake, lookback_hours=0)
    assert len(fake.sent("startCommandExecutionOnEndpoint")) == 1


def test_a_failed_and_a_timed_out_command_are_gaps() -> None:
    fake = FakeGravityZone(
        [endpoint("fail"), endpoint("slow"), endpoint("ok")],
        {"fail": "failed", "slow": "pending", "ok": CODEX},
    )
    clock = FakeClock()
    connector = connector_for(fake, clock)
    records = agent_records([scan_all(fake, connector=connector)])

    assert len(records) == 1
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {
        "command-failed": 1,
        "command-timed-out": 1,
    }
    assert clock.now >= gz.COMMAND_TIMEOUT_SECONDS


def test_one_refused_command_is_a_gap_and_the_rest_are_read() -> None:
    fake = FakeGravityZone(
        [endpoint("refused"), endpoint("ok")],
        {"refused": 403, "ok": CODEX},
    )
    connector = connector_for(fake)
    assert len(agent_records([scan_all(fake, connector=connector)])) == 1
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"command-refused": 1}


def test_a_command_refused_on_every_endpoint_fails_the_scan_as_permission_denied() -> (
    None
):
    """That is the key, the role or the licence, not the fleet."""
    fake = FakeGravityZone([endpoint("a"), endpoint("b")], {"a": 403, "b": 403})
    with pytest.raises(GravityZoneError) as caught:
        scan_all(fake)
    assert caught.value.status_code == 403
    assert "Investigation API" in str(caught.value)
    assert failure_code(caught.value) is DiscoveryErrorCode.PERMISSION_DENIED


def test_commands_go_out_in_bounded_waves() -> None:
    count = gz.WAVE_SIZE + 3
    fake = FakeGravityZone(
        [endpoint(f"e{i}") for i in range(count)],
        {f"e{i}": CODEX for i in range(count)},
    )
    scan_all(fake)
    methods = [m for m, _ in fake.calls if m != "getManagedEndpointDetails"]
    first_poll = methods.index("getInvestigationFileUrl")
    assert methods[:first_poll].count("startCommandExecutionOnEndpoint") == gz.WAVE_SIZE


# --- the key and the API --------------------------------------------------------


def test_every_call_is_json_rpc_with_the_key_as_basic_user_and_no_redirects() -> None:
    fake = FakeGravityZone([endpoint("e1")], {"e1": CODEX})
    scan_all(fake)
    expected = "Basic " + base64.b64encode(f"{API_KEY}:".encode()).decode()
    for post in fake.posts:
        assert post["headers"]["Authorization"] == expected
        assert post["allow_redirects"] is False
        assert post["json"]["jsonrpc"] == "2.0"
        assert post["url"].startswith(f"{ACCESS_URL}/v1.0/jsonrpc/")
    assert sum(TIMEOUT) < 120
    urls = {p["json"]["method"]: p["url"] for p in fake.posts}
    assert urls["getEndpointsList"].endswith("/jsonrpc/network")
    assert urls["startCommandExecutionOnEndpoint"].endswith("/jsonrpc/investigation")


def test_the_roster_is_paged_until_no_more_records_and_never_repeats_an_id() -> None:
    eps = [endpoint(f"e{i}", state=2) for i in range(5)]
    fake = FakeGravityZone(eps + [eps[0]], per_page=2)
    client = GravityZoneClient(
        GravityZoneSettings(ACCESS_URL, API_KEY, page_size=2),
        session=fake,  # type: ignore[arg-type]
        sleep=lambda _s: None,
    )
    assert [e["id"] for e in client.endpoints()] == [f"e{i}" for i in range(5)]
    pages = fake.sent("getEndpointsList")
    assert [p["page"] for p in pages] == [1, 2, 3]
    assert all(p["isManaged"] is True and p["perPage"] == 2 for p in pages)


def test_the_key_goes_to_the_access_url_host_and_not_to_a_storage_url() -> None:
    ours = FakeGravityZone([endpoint("e1")], {"e1": CODEX})
    scan_all(ours)
    assert "Authorization" in ours.downloads[0]["headers"]
    assert ours.downloads[0]["allow_redirects"] is False

    storage = FakeGravityZone(
        [endpoint("e1")],
        {"e1": CODEX},
        download_host="bucket.s3.amazonaws.com",
    )
    scan_all(storage)
    assert storage.downloads[0]["headers"] == {}


def test_a_refused_key_fails_the_scan_as_authentication() -> None:
    fake = FakeGravityZone([endpoint("e1")], statuses={"getEndpointsList": [401]})
    with pytest.raises(GravityZoneError) as caught:
        scan_all(fake)
    assert caught.value.status_code == 401
    assert "api_key" in str(caught.value)
    assert failure_code(caught.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_key_without_the_investigation_api_fails_before_any_command() -> None:
    fake = FakeGravityZone([endpoint("e1")], {"e1": CODEX}, enabled_apis=["network"])
    with pytest.raises(GravityZoneError) as caught:
        scan_all(fake)
    assert caught.value.status_code == 403
    assert fake.sent("startCommandExecutionOnEndpoint") == []
    assert fake.sent("getEndpointsList") == []


def test_a_key_whose_apis_cannot_be_read_is_not_refused_for_it() -> None:
    fake = FakeGravityZone([endpoint("e1")], {"e1": CODEX}, enabled_apis=None)
    assert len(agent_records([scan_all(fake)])) == 1


def test_a_429_is_retried_but_a_5xx_never_restarts_a_command() -> None:
    fake = FakeGravityZone(
        [endpoint("e1"), endpoint("e2")],
        {"e1": CODEX, "e2": CODEX},
        statuses={
            "getEndpointsList": [429],
            "startCommandExecutionOnEndpoint": [503],
        },
    )
    connector = connector_for(fake)
    records = agent_records([scan_all(fake, connector=connector)])
    assert len(fake.sent("getEndpointsList")) == 2
    # e1's start got the 503 and was not retried; e2's went through.
    assert len(fake.sent("startCommandExecutionOnEndpoint")) == 2
    assert len(records) == 1
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"command-refused": 1}


def test_a_200_that_is_not_json_rpc_is_the_vendors_error() -> None:
    class HtmlProxy(FakeGravityZone):
        def post(self, url: str, **kw: Any) -> FakeResponse:
            return FakeResponse(200, None)

    with pytest.raises(GravityZoneError) as caught:
        scan_all(HtmlProxy([]))
    assert caught.value.status_code == 200
    assert "access_url" in str(caught.value)


def test_an_unreachable_host_stays_a_connection_error() -> None:
    class Down(FakeGravityZone):
        def post(self, url: str, **kw: Any) -> FakeResponse:
            raise requests.ConnectionError("refused")

    with pytest.raises(requests.ConnectionError) as caught:
        scan_all(Down([]))
    assert "cloudgz.gravityzone.bitdefender.com" in str(caught.value)


def test_a_stop_ends_the_scan_without_another_call() -> None:
    fake = FakeGravityZone([endpoint(f"e{i}", state=2) for i in range(3)])
    connector = connector_for(fake)
    connector.stop_when(lambda: True)
    scan_all(fake, connector=connector)
    assert len(fake.sent("getManagedEndpointDetails")) == 1
    assert fake.sent("startCommandExecutionOnEndpoint") == []


def test_neither_the_key_nor_the_value_is_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeGravityZone(
        [endpoint("e1"), endpoint("bad")],
        {"e1": CODEX, "bad": "arthur1.not-base64!"},
    )
    with caplog.at_level(logging.DEBUG):
        scan_all(fake)
    text = caplog.text
    assert API_KEY not in text
    assert base64.b64encode(f"{API_KEY}:".encode()).decode() not in text
    assert CODEX not in text


# --- configuration --------------------------------------------------------------


@pytest.mark.parametrize("missing", ["access_url", "api_key"])
def test_a_missing_field_is_named(missing: str) -> None:
    creds = {k: v for k, v in CREDS.items() if k != missing}
    fields = {k: v for k, v in FIELDS.items() if k != missing}
    with pytest.raises(DiscoveryConfigurationError, match=missing):
        _settings_from(creds, fields)


@pytest.mark.parametrize(
    "url",
    [
        "http://cloudgz.gravityzone.bitdefender.com/api",
        "https://user:pw@cloudgz.gravityzone.bitdefender.com/api",
        "https://cloudgz..bitdefender.com:99999/api",
    ],
)
def test_an_access_url_the_key_must_not_be_sent_to_is_refused(url: str) -> None:
    with pytest.raises(DiscoveryConfigurationError) as caught:
        _settings_from(CREDS, {"access_url": url})
    assert "pw" not in str(caught.value)
    assert failure_code(caught.value) is DiscoveryErrorCode.NOT_CONFIGURED
