"""The Compute Engine client and connector, against a fake Compute Engine API.

What matters most here is what a VM that cannot report looks like. Guest attributes keep
serving their last values after a VM stops or has the setting turned off, and a VM the
collector never reached has no namespace at all -- each of those must be counted and
named, never published as a clean machine or as a live report.
"""

import base64
import gzip
import io
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

import pytest
import requests
import yaml
from arthur_client.api_bindings import DiscoveryRunStatus
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    Platform,
    RunsOn,
    SourceAddress,
)
from google.auth.exceptions import RefreshError

from discovery import source_connectors
from discovery.cloud.gce import client as gce_client
from discovery.cloud.gce.client import (
    CLOUD_PLATFORM_READONLY_SCOPE,
    COMPUTE_READONLY_SCOPE,
    RESOURCE_MANAGER_API,
    ComputeEngineError,
)
from discovery.cloud.gce.connector import (
    ALLOW_ADC_ENV_VAR,
    GUEST_ATTRIBUTES_DISABLED,
    NOT_REPORTED_IN_WINDOW,
    OSCONFIG_DISABLED,
    READ_FAILED,
    VENDOR,
    ComputeEngineConnector,
    parse_label_selectors,
    settings_from,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_run_reporter import platform_outcome
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    MAX_UNREADABLE_DEVICES,
    AcceptsStopCheck,
    DeniedScope,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    DiscoveryPublishResult,
    DiscoveryScanOutcome,
    ReportsDeniedScopes,
    ReportsDeviceCoverage,
    failure_code,
    run_source_scan,
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
                "platforms": ["darwin", "linux"],
                "npm": ["@openai/codex"],
            },
        ],
    },
)
PROJECT = "acme-prod-123"
ZONE = "us-central1-a"
FIELDS = {"project_ids": PROJECT}
API = gce_client.COMPUTE_API


def frame(rows: list[dict[str, str]]) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(json.dumps(rows).encode())
    return "arthur1." + base64.b64encode(buf.getvalue()).decode()


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


CODEX = frame(
    [
        row("npm", "@openai/codex", ver="0.5.0"),
        row("scan", "packages-linux", ver=str(SCAN_AT), extra="ok"),
    ],
)
OK_STATUS = "ok 2026-10-12T12:58:28Z rows=2 packages-linux=ok"
# The scan's clock: half an hour after OK_STATUS, inside the default 24h lookback.
NOW = datetime(2026, 10, 12, 13, 30, tzinfo=timezone.utc)


def vm(
    ident: str,
    name: Optional[str] = None,
    zone: str = ZONE,
    status: str = "RUNNING",
    labels: Optional[dict[str, str]] = None,
    flag: Optional[str] = None,
    project: str = PROJECT,
    osconfig: Optional[str] = None,
) -> dict[str, Any]:
    """A VM as `aggregated/instances` returns it."""
    record: dict[str, Any] = {
        "id": ident,
        "name": name or f"vm-{ident}",
        "zone": f"{API}/projects/{project}/zones/{zone}",
        "status": status,
        "labels": labels or {},
        "metadata": {
            "items": [
                # Metadata a scan must not read, keep or log.
                {"key": "startup-script", "value": "echo secret-ish"},
            ],
        },
    }
    if flag is not None:
        record["metadata"]["items"].append(
            {"key": "enable-guest-attributes", "value": flag},
        )
    if osconfig is not None:
        record["metadata"]["items"].append(
            {"key": "enable-osconfig", "value": osconfig},
        )
    return record


def attributes(inventory: str, status: str = OK_STATUS) -> dict[str, Any]:
    """A `getGuestAttributes` answer for the `arthur/` namespace."""
    return {
        "queryPath": "arthur/",
        "queryValue": {
            "items": [
                {"namespace": "arthur", "key": "inventory", "value": inventory},
                {"namespace": "arthur", "key": "status", "value": status},
            ],
        },
    }


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status_code = status
        self._body = body
        self.headers = headers or {}

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no body")
        return self._body


class FakeCompute:
    """Compute Engine's three read calls, Resource Manager's two, and a log of what was
    asked.

    `pages[project]` is the listing's pages; `project_flag[project]` the project's
    `enable-guest-attributes` and `project_osconfig[project]` its `enable-osconfig`,
    each absent when unset; `guest[(zone, name)]` a VM's answer, missing for 404, or a
    list of responses to hand out in turn. `children[parent]` is what Resource Manager
    lists under an organization or folder: `(project id, state)` and `(folder name,
    state)` pairs. `listing[project]` answers a project's listing instead of its pages,
    and `resource_manager` answers every Resource Manager call.
    """

    def __init__(
        self,
        pages: dict[str, list[list[dict[str, Any]]]],
        project_flag: Optional[dict[str, str]] = None,
        guest: Optional[dict[tuple[str, str], Any]] = None,
        unreachables: Optional[list[str]] = None,
        project_osconfig: Optional[dict[str, str]] = None,
        children: Optional[dict[str, dict[str, list[tuple[str, str]]]]] = None,
        listing: Optional[dict[str, FakeResponse]] = None,
        resource_manager: Optional[FakeResponse] = None,
    ) -> None:
        self.pages = pages
        self.project_flag = {PROJECT: "TRUE"} if project_flag is None else project_flag
        self.project_osconfig = (
            {PROJECT: "TRUE"} if project_osconfig is None else project_osconfig
        )
        self.guest = guest or {}
        self.unreachables = unreachables or []
        self.children = children or {}
        self.listing = listing or {}
        self.resource_manager = resource_manager
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.scopes: Sequence[str] = ()

    def get(self, url: str, params: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append((url, dict(params)))
        if url.startswith(RESOURCE_MANAGER_API):
            return self._resource_manager(
                url.removeprefix(RESOURCE_MANAGER_API),
                params,
            )
        path = url.removeprefix(API)
        parts = path.strip("/").split("/")

        if parts[2:] == ["aggregated", "instances"]:
            if parts[1] in self.listing:
                return self.listing[parts[1]]
            pages = self.pages.get(parts[1], [[]])
            index = int(params.get("pageToken") or 0)
            body: dict[str, Any] = {
                "items": {
                    f"zones/{ZONE}": {"instances": pages[index]},
                    "zones/europe-west1-b": {
                        "warning": {"code": "NO_RESULTS_ON_PAGE"},
                    },
                },
            }
            if index + 1 < len(pages):
                body["nextPageToken"] = str(index + 1)
            if self.unreachables and index == 0:
                body["unreachables"] = self.unreachables
            return FakeResponse(200, body)

        if len(parts) == 2:
            items = [
                {"key": key, "value": value}
                for key, value in (
                    ("enable-guest-attributes", self.project_flag.get(parts[1])),
                    ("enable-osconfig", self.project_osconfig.get(parts[1])),
                )
                if value
            ]
            return FakeResponse(200, {"commonInstanceMetadata": {"items": items}})

        if parts[-1] == "getGuestAttributes":
            answer = self.guest.get((parts[3], parts[5]))
            if isinstance(answer, list):
                answer = answer.pop(0)
            if isinstance(answer, FakeResponse):
                return answer
            if answer is None:
                return FakeResponse(
                    404,
                    {"error": {"code": 404, "message": "guestAttributes not found"}},
                )
            return FakeResponse(200, answer)

        raise AssertionError(f"unexpected call {url}")

    def _resource_manager(self, path: str, params: dict[str, Any]) -> FakeResponse:
        if self.resource_manager is not None:
            return self.resource_manager
        kind = path.strip("/")
        assert kind in ("projects", "folders"), path
        assert params.get("pageSize"), "a listing names its page size"
        listed = self.children.get(params["parent"], {}).get(kind, [])
        # One child per page, so paging is exercised on every walk.
        index = int(params.get("pageToken") or 0)
        body: dict[str, Any] = {kind: []}
        if index < len(listed):
            ident, state = listed[index]
            body[kind] = [
                (
                    {"projectId": ident, "name": f"projects/{index}", "state": state}
                    if kind == "projects"
                    else {"name": ident, "displayName": ident, "state": state}
                ),
            ]
        if index + 1 < len(listed):
            body["nextPageToken"] = str(index + 1)
        return FakeResponse(200, body)

    def reads(self) -> list[str]:
        """The VMs whose guest attributes were read, by name."""
        return [
            url.split("/")[-2]
            for url, _ in self.calls
            if url.endswith("/getGuestAttributes")
        ]

    def listed(self) -> list[str]:
        """The projects whose VMs were listed, in order."""
        return [
            url.removeprefix(API).split("/")[2]
            for url, params in self.calls
            if url.endswith("/aggregated/instances") and not params.get("pageToken")
        ]


class FakeConfig:
    def __init__(self, query: Optional[str] = CATALOG) -> None:
        self.query = query
        self.vendor = VENDOR
        self.name = "acme gce"


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gce_client, "backoff_seconds", lambda attempt, after: 0.0)


@pytest.fixture(autouse=True)
def adc(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keyless sources, so no test needs a real service account key."""
    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "true")


def connector_for(fake: FakeCompute) -> ComputeEngineConnector:
    def session_for(creds: Any, scopes: Sequence[str]) -> FakeCompute:
        fake.scopes = tuple(scopes)
        return fake

    return ComputeEngineConnector(session_for=session_for, clock=lambda: NOW)  # type: ignore[arg-type]


def scan(
    fake: FakeCompute,
    fields: Optional[dict[str, str]] = None,
    connector: Optional[ComputeEngineConnector] = None,
    lookback_hours: int = 24,
    credentials: Optional[dict[str, str]] = None,
) -> list[Any]:
    connector = connector or connector_for(fake)
    batches = connector.scan(
        FakeConfig(),  # type: ignore[arg-type]
        lookback_hours,
        credentials or {},
        fields or FIELDS,
        LOG,
    )
    return [record for batch in batches for record in batch]


def listed(connector: ComputeEngineConnector) -> list[dict[str, Any]]:
    """The unreadable VMs the scan listed, as the run's coverage carries them."""
    coverage = connector.device_coverage()
    assert coverage is not None
    return [asdict(device) for device in coverage.unreadable_devices]


# --- records --------------------------------------------------------------------------


def test_a_reporting_vm_is_a_cloud_record_on_gcp_addressed_by_vm_project_and_zone() -> (
    None
):
    """A cloud record, as the catalog classes the vendor, addressed per (software, VM):
    the VM is the instance, so no two VMs in a project are one agent."""
    fake = FakeCompute(
        {PROJECT: [[vm("4823710983451", name="build-1")]]},
        guest={(ZONE, "build-1"): attributes(CODEX)},
    )
    records = scan(fake)

    assert len(records) == 1
    record = records[0]
    assert record.external_id == "4823710983451:codex-cli"
    assert record.runs_on is RunsOn.GCP
    assert record.platform is Platform.LINUX
    assert record.last_seen == datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
    check_batch(records, "Source config 'acme gce' (gcp_compute_engine)")
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.type == "CLOUD"
    assert source.vendor == "gcp_compute_engine"
    assert source.address == SourceAddress(
        instance="4823710983451",
        scope=f"{PROJECT}/{ZONE}",
        resource_kind="npm",
        resource_id="@openai/codex",
    )
    assert source.observations is not None
    assert source.observations.host_name == "build-1"


def test_a_vm_recreated_under_the_same_name_is_a_new_machine() -> None:
    """The name is reused on delete-and-recreate; the instance id is not."""
    before = FakeCompute(
        {PROJECT: [[vm("111", name="build-1")]]},
        guest={(ZONE, "build-1"): attributes(CODEX)},
    )
    # Deleted and recreated in the same project and zone, under the same name.
    after = FakeCompute(
        {PROJECT: [[vm("222", name="build-1")]]},
        guest={(ZONE, "build-1"): attributes(CODEX)},
    )
    [first], [second] = scan(before), scan(after)

    assert (first.external_id, second.external_id) == ("111:codex-cli", "222:codex-cli")
    assert first.creation_source.address.instance == "111"
    assert second.creation_source.address.instance == "222"


def test_every_page_of_every_project_is_read_and_an_unreachable_zone_is_named(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeCompute(
        {
            PROJECT: [[vm("1"), vm("2")], [vm("3")]],
            "acme-dev-456": [[vm("4", project="acme-dev-456")]],
        },
        project_flag={PROJECT: "TRUE", "acme-dev-456": "TRUE"},
        guest={(ZONE, f"vm-{i}"): attributes(CODEX) for i in "1234"},
        unreachables=["zones/asia-east1-a"],
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.INFO):
        records = scan(fake, {"project_ids": f"{PROJECT},acme-dev-456"}, connector)

    assert len(records) == 4
    coverage = connector.device_coverage()
    assert coverage is not None
    assert (coverage.devices_read, coverage.devices_decoded) == (4, 4)
    assert "zones/asia-east1-a" in caplog.text
    assert "missing from this scan" in caplog.text
    assert "secret-ish" not in caplog.text, "metadata is never logged"


def test_a_stopped_vm_is_still_read_and_its_records_are_dated_by_its_scan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeCompute(
        {
            PROJECT: [
                [
                    vm("1", status="TERMINATED"),
                    # Not read, so not among the VMs whose values are called old.
                    vm("2", status="TERMINATED", flag="FALSE"),
                ],
            ],
        },
        guest={(ZONE, "vm-1"): attributes(CODEX), (ZONE, "vm-2"): attributes(CODEX)},
    )
    with caplog.at_level(logging.INFO):
        records = scan(fake)

    assert records[0].last_seen == datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
    assert "1 in-scope VM(s) were not running (TERMINATED: 1)" in caplog.text


def test_a_vm_that_has_not_reported_in_the_lookback_is_counted_and_not_published(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Its last values are still served, and publishing them again would keep its agents
    fresh on the Platform, which dates evidence by when a scan last handed it over."""
    days_ago = "ok 2026-10-09T08:00:00Z rows=2 packages-linux=ok"
    no_status = {
        "queryPath": "arthur/",
        "queryValue": {
            "items": [{"namespace": "arthur", "key": "inventory", "value": CODEX}],
        },
    }
    fake = FakeCompute(
        {
            PROJECT: [
                [
                    # Stopped three days ago.
                    vm("1", status="TERMINATED"),
                    # Running, its collector failing: the last good scan still counts,
                    # as a Jamf Mac's does while it checks in.
                    vm("2"),
                    # No status line, so its payload's own scan dates it.
                    vm("3"),
                    # A stamp that is not a time is skipped, not fatal.
                    vm("4"),
                    vm("5"),
                ],
            ],
        },
        guest={
            (ZONE, "vm-1"): attributes(CODEX, days_ago),
            (ZONE, "vm-2"): attributes(
                CODEX,
                f"{days_ago} failed=2026-10-12T13:05:00Z osquery=absent",
            ),
            (ZONE, "vm-3"): no_status,
            (ZONE, "vm-4"): attributes(CODEX, "ok 2026-13-45T08:00:00Z rows=2"),
            (ZONE, "vm-5"): attributes(CODEX),
        },
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.INFO):
        records = scan(fake, connector=connector)

    assert sorted(r.external_id for r in records) == ["2:codex-cli", "5:codex-cli"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {NOT_REPORTED_IN_WINDOW: 3}
    assert "not running" not in caplog.text, "the stopped VM was left out"
    assert "1 VM(s) report that their collector's latest run failed" in caplog.text

    # A lookback of zero asks for every VM's last report, as on Jamf.
    assert len(scan(fake, lookback_hours=0)) == 5


# --- VMs that cannot report -------------------------------------------------------------


@pytest.mark.parametrize(
    "instance_flag,project_flag,read",
    [
        (None, "TRUE", True),
        ("TRUE", None, True),
        ("true", "FALSE", True),
        ("FALSE", "TRUE", False),
        (None, None, False),
        (None, "FALSE", False),
    ],
)
def test_guest_attributes_off_is_counted_by_name_and_not_read(
    instance_flag: Optional[str],
    project_flag: Optional[str],
    read: bool,
) -> None:
    """The API keeps serving a VM's last values after the setting is turned off, so
    reading them would publish a machine that cannot have reported since."""
    fake = FakeCompute(
        {PROJECT: [[vm("1", flag=instance_flag)]]},
        project_flag={PROJECT: project_flag} if project_flag else {},
        guest={(ZONE, "vm-1"): attributes(CODEX)},
    )
    connector = connector_for(fake)
    records = scan(fake, connector=connector)

    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_in_scope == 1
    # The project's default is asked for only when the VM does not say, so a role
    # without compute.projects.get still scans a fleet that sets it per VM.
    project_reads = [url for url, _ in fake.calls if url == f"{API}/projects/{PROJECT}"]
    assert len(project_reads) == (1 if instance_flag is None else 0)
    if read:
        assert len(records) == 1
        assert fake.reads() == ["vm-1"]
    else:
        assert records == []
        assert fake.reads() == []
        assert coverage.unreadable_by_reason == {GUEST_ATTRIBUTES_DISABLED: 1}


def test_a_vm_the_collector_never_reached_is_counted_and_the_fleet_is_not_called_clean(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeCompute({PROJECT: [[vm("1")]]}, guest={})
    connector = connector_for(fake)
    with caplog.at_level(logging.WARNING):
        records = scan(fake, connector=connector)

    assert records == []
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"never-reported": 1}
    assert listed(connector) == [
        {
            "device_key": "1",
            "name": "vm-1",
            "location": f"{PROJECT}/{ZONE}",
            "reason": "never-reported",
            "last_reported": None,
        },
    ]
    assert "decoded 0 of 1 VM(s)" in caplog.text
    assert "device_coverage.unreadable_devices" in caplog.text


@pytest.mark.parametrize(
    "instance_osconfig,project_osconfig,reason",
    [
        (None, "TRUE", "never-reported"),
        ("TRUE", "FALSE", "never-reported"),
        ("FALSE", "TRUE", OSCONFIG_DISABLED),
        (None, "FALSE", OSCONFIG_DISABLED),
        (None, None, OSCONFIG_DISABLED),
    ],
)
def test_a_vm_nothing_was_written_for_with_osconfig_off_can_never_be_reached(
    instance_osconfig: Optional[str],
    project_osconfig: Optional[str],
    reason: str,
) -> None:
    """The OS policy installs the collector through the OS Config agent, which acts only
    where enable-osconfig is true. Off, the rollout cannot reach the VM, which is not
    the same fact as a rollout that has not reached it yet."""
    # The VM sets guest attributes itself, so the only project read is for osconfig.
    fake = FakeCompute(
        {PROJECT: [[vm("1", flag="TRUE", osconfig=instance_osconfig)]]},
        guest={},
        project_osconfig={PROJECT: project_osconfig} if project_osconfig else {},
    )
    connector = connector_for(fake)
    assert scan(fake, connector=connector) == []

    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {reason: 1}
    assert [d["reason"] for d in listed(connector)] == [reason]
    # The project is read once, for both keys, and only when the VM does not say.
    project_reads = [url for url, _ in fake.calls if url == f"{API}/projects/{PROJECT}"]
    assert len(project_reads) == (1 if instance_osconfig is None else 0)


def test_a_vm_that_has_reported_keeps_its_own_reasons_whatever_osconfig_says() -> None:
    """What it wrote is evidence; the key says only what the agent will do next."""
    fake = FakeCompute(
        {PROJECT: [[vm("1", osconfig="FALSE"), vm("2", osconfig="FALSE")]]},
        guest={
            (ZONE, "vm-1"): attributes(CODEX),
            (ZONE, "vm-2"): attributes("no-cache", "no-cache"),
        },
        project_osconfig={},
    )
    connector = connector_for(fake)
    records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["1:codex-cli"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"no-cache": 1}


def test_every_unreadable_vm_is_listed_by_id_location_and_reason() -> None:
    """The machines a scan cannot see are where unmanaged AI sits, so each is a
    finding by identity, not a number."""
    days_ago = "ok 2026-10-09T08:00:00Z rows=2 packages-linux=ok"
    fake = FakeCompute(
        {
            PROJECT: [
                [
                    vm("1", name="stale", status="TERMINATED"),
                    vm("2", name="no-attrs", flag="FALSE"),
                    vm("3", name="broken"),
                    vm("4", name="no-cache"),
                    vm("5", name="fine"),
                ],
            ],
        },
        guest={
            (ZONE, "stale"): attributes(CODEX, days_ago),
            (ZONE, "broken"): [FakeResponse(500, {"error": {"message": "x"}})] * 5,
            (ZONE, "no-cache"): attributes("no-cache", "no-cache"),
            (ZONE, "fine"): attributes(CODEX),
        },
    )
    connector = connector_for(fake)
    records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["5:codex-cli"]
    assert listed(connector) == [
        {
            "device_key": "1",
            "name": "stale",
            "location": f"{PROJECT}/{ZONE}",
            "reason": NOT_REPORTED_IN_WINDOW,
            "last_reported": "2026-10-09T08:00:00+00:00",
        },
        {
            "device_key": "2",
            "name": "no-attrs",
            "location": f"{PROJECT}/{ZONE}",
            "reason": GUEST_ATTRIBUTES_DISABLED,
            "last_reported": None,
        },
        {
            "device_key": "3",
            "name": "broken",
            "location": f"{PROJECT}/{ZONE}",
            "reason": READ_FAILED,
            "last_reported": None,
        },
        {
            "device_key": "4",
            "name": "no-cache",
            "location": f"{PROJECT}/{ZONE}",
            "reason": "no-cache",
            "last_reported": None,
        },
    ]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_unreadable == 4
    assert coverage.unreadable_devices_truncated == 0


def test_the_list_stops_at_the_cap_and_the_counts_do_not() -> None:
    fleet = [vm(str(i)) for i in range(MAX_UNREADABLE_DEVICES + 1)]
    fake = FakeCompute({PROJECT: [fleet]}, guest={})
    connector = connector_for(fake)
    assert scan(fake, connector=connector) == []

    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_unreadable == MAX_UNREADABLE_DEVICES + 1
    assert coverage.unreadable_by_reason == {
        "never-reported": MAX_UNREADABLE_DEVICES + 1,
    }
    assert len(coverage.unreadable_devices) == MAX_UNREADABLE_DEVICES
    assert coverage.unreadable_devices_truncated == 1
    assert [d.device_key for d in coverage.unreadable_devices[:2]] == ["0", "1"]


def test_a_failed_run_keeps_the_last_good_scan_and_is_named(
    caplog: pytest.LogCaptureFixture,
) -> None:
    status = f"{OK_STATUS} failed=2026-10-12T12:59:40Z osquery=absent"
    fake = FakeCompute(
        {PROJECT: [[vm("1"), vm("2")]]},
        guest={
            (ZONE, "vm-1"): attributes(CODEX, status),
            (ZONE, "vm-2"): attributes(
                "no-cache",
                "no-cache failed=2026-10-12T12:59:52Z osquery=absent",
            ),
        },
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.WARNING):
        records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["1:codex-cli"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {"no-cache": 1}
    assert "2 VM(s) report that their collector's latest run failed" in caplog.text
    assert "osquery=absent: 2" in caplog.text


def test_one_unreadable_vm_is_reported_and_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeCompute(
        {PROJECT: [[vm("1"), vm("2"), vm("3")]]},
        guest={
            (ZONE, "vm-1"): FakeResponse(500, {"error": {"message": "backend"}}),
            (ZONE, "vm-2"): attributes(CODEX),
            # A 200 whose body is not JSON: a proxy's page, or a cut-off answer.
            (ZONE, "vm-3"): FakeResponse(200),
        },
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.WARNING):
        records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["2:codex-cli"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {READ_FAILED: 2}
    assert "1: guest attributes not read" in caplog.text
    assert "3: guest attributes not read" in caplog.text
    assert "not JSON" in caplog.text
    assert fake.reads().count("vm-1") == 5, "retried before giving up"


RATE_LIMITED = FakeResponse(
    403,
    {"error": {"code": 403, "errors": [{"reason": "rateLimitExceeded"}]}},
)


def test_a_rate_limit_sent_as_403_is_retried() -> None:
    fake = FakeCompute(
        {PROJECT: [[vm("1")]]},
        guest={(ZONE, "vm-1"): [RATE_LIMITED, FakeResponse(200, attributes(CODEX))]},
    )
    assert len(scan(fake)) == 1


def test_a_rate_limit_that_outlasts_its_retries_is_not_a_denied_permission() -> None:
    """Read as the 403 it was sent as, it would end the scan as permission denied."""
    fake = FakeCompute(
        {PROJECT: [[vm("1"), vm("2")]]},
        guest={(ZONE, "vm-1"): [RATE_LIMITED] * 5, (ZONE, "vm-2"): attributes(CODEX)},
    )
    connector = connector_for(fake)
    records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["2:codex-cli"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {READ_FAILED: 1}

    class Limited(FakeCompute):
        def get(self, url: str, params: dict[str, Any], timeout: float) -> Any:
            return RATE_LIMITED

    with pytest.raises(ComputeEngineError) as exc:
        scan(Limited({}))

    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


def test_a_denied_permission_ends_the_scan_as_permission_denied() -> None:
    """Not one VM's problem: every VM behind it would fail the same way."""
    denied = FakeResponse(
        403,
        {
            "error": {
                "code": 403,
                "message": "Required 'compute.instances.getGuestAttributes' permission",
                "errors": [{"reason": "forbidden"}],
            },
        },
    )
    fake = FakeCompute(
        {PROJECT: [[vm("1"), vm("2")]]},
        guest={(ZONE, "vm-1"): denied, (ZONE, "vm-2"): attributes(CODEX)},
    )
    with pytest.raises(ComputeEngineError) as exc:
        scan(fake)

    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert "compute.instances.getGuestAttributes" in str(exc.value)
    assert fake.reads() == ["vm-1"]


def test_a_refused_credential_ends_the_scan_as_authentication_failed() -> None:
    class Refusing(FakeCompute):
        def get(self, url: str, params: dict[str, Any], timeout: float) -> Any:
            raise RefreshError("invalid_grant: account not found", retryable=False)

    with pytest.raises(RefreshError) as exc:
        scan(Refusing({}))

    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_an_unreachable_api_is_retried_then_reported() -> None:
    class Unreachable(FakeCompute):
        def get(self, url: str, params: dict[str, Any], timeout: float) -> Any:
            self.calls.append((url, params))
            raise requests.ConnectionError("reset")

    fake = Unreachable({})
    with pytest.raises(ComputeEngineError, match="unreachable"):
        scan(fake)

    assert len(fake.calls) == 5
    assert failure_code(ComputeEngineError("x")) is DiscoveryErrorCode.PROVIDER_ERROR


# --- label scope ----------------------------------------------------------------------


def test_label_scope_reads_only_the_vms_it_admits_and_counts_each_selector(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeCompute(
        {
            PROJECT: [
                [
                    vm("1", labels={"env": "prod"}),
                    vm("2", labels={"env": "prod", "team": "contractors"}),
                    vm("3", labels={"env": "dev"}),
                    vm("4", labels={"team": "ml"}),
                ],
            ],
        },
        guest={(ZONE, f"vm-{i}"): attributes(CODEX) for i in "1234"},
    )
    connector = connector_for(fake)
    fields = {
        "project_ids": PROJECT,
        "include_labels": "env=prod, team = ml, env=staging",
        "exclude_labels": "team=contractors",
    }
    with caplog.at_level(logging.INFO):
        records = scan(fake, fields, connector)

    assert sorted(r.external_id for r in records) == ["1:codex-cli", "4:codex-cli"]
    assert sorted(fake.reads()) == ["vm-1", "vm-4"], "out of scope is never read"
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_read == 4
    assert coverage.devices_in_scope == 2
    assert coverage.devices_excluded == 1
    assert coverage.excluded_by_group == {"team=contractors": 1}
    assert coverage.devices_outside_included_groups == 1
    assert coverage.included_by_group == {"env=prod": 1, "team=ml": 1, "env=staging": 0}
    # A selector no VM carries is a zero and a warning, not a failed scan.
    assert "no VM read carries label selector(s) env=staging" in caplog.text


def test_a_scope_that_keeps_nothing_says_so(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeCompute({PROJECT: [[vm("1", labels={"env": "dev"})]]})
    with caplog.at_level(logging.WARNING):
        records = scan(fake, {"project_ids": PROJECT, "include_labels": "env=prod"})

    assert records == []
    assert "left all 1 VM(s) it read out of scope" in caplog.text


# --- an organization or a folder as the roster --------------------------------------


ORG = "organizations/123456789"
FORBIDDEN = FakeResponse(
    403,
    {
        "error": {
            "code": 403,
            "message": "Required 'compute.instances.list' permission",
            "errors": [{"reason": "forbidden"}],
        },
    },
)
NO_COMPUTE_API = FakeResponse(
    403,
    {
        "error": {
            "code": 403,
            "message": "Compute Engine API has not been used in project acme-docs",
            "errors": [{"reason": "accessNotConfigured"}],
        },
    },
)


def org_fake(**over: Any) -> FakeCompute:
    """An organization of four projects: two at the top, one in a folder, one in a
    folder inside it, plus one being deleted. Every VM reports."""
    projects = ["acme-prod-123", "acme-dev-456", "acme-ml-789", "acme-old-000"]
    args: dict[str, Any] = dict(
        pages={p: [[vm(str(i), project=p)]] for i, p in enumerate(projects, 1)},
        project_flag={p: "TRUE" for p in projects},
        project_osconfig={p: "TRUE" for p in projects},
        guest={(ZONE, f"vm-{i}"): attributes(CODEX) for i in "1234"},
        children={
            ORG: {
                "projects": [
                    ("acme-prod-123", "ACTIVE"),
                    ("acme-dev-456", "ACTIVE"),
                    ("acme-gone-111", "DELETE_REQUESTED"),
                ],
                "folders": [("folders/555", "ACTIVE")],
            },
            "folders/555": {
                "projects": [("acme-ml-789", "ACTIVE")],
                "folders": [("folders/777", "ACTIVE")],
            },
            "folders/777": {"projects": [("acme-old-000", "ACTIVE")], "folders": []},
        },
    )
    args.update(over)
    return FakeCompute(**args)


def test_every_active_project_under_the_organization_is_listed_once_and_scanned(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Folders are walked; a project named as well as listed is read once; a project
    being deleted is left out; and the token carries the Resource Manager scope."""
    fake = org_fake()
    connector = connector_for(fake)
    with caplog.at_level(logging.INFO):
        records = scan(
            fake,
            {"organization_id": "123456789", "project_ids": "acme-dev-456"},
            connector,
        )

    assert sorted(r.external_id for r in records) == [f"{i}:codex-cli" for i in "1234"]
    assert fake.listed() == [
        "acme-dev-456",
        "acme-prod-123",
        "acme-ml-789",
        "acme-old-000",
    ]
    assert fake.scopes == (COMPUTE_READONLY_SCOPE, CLOUD_PLATFORM_READONLY_SCOPE)
    assert connector.denied_scopes() == ()
    assert "4 project(s) (3 under organizations/123456789)" in caplog.text
    assert "3 project(s) under organizations/123456789; 0 without" in caplog.text


def test_folders_alone_are_a_scope_and_a_source_without_parents_keeps_its_scope() -> (
    None
):
    fake = org_fake()
    assert [r.external_id for r in scan(fake, {"folder_ids": "555, 777"})] == [
        "3:codex-cli",
        "4:codex-cli",
    ]
    assert fake.listed() == ["acme-ml-789", "acme-old-000"], "777 is under 555 too"

    plain = FakeCompute(
        {PROJECT: [[vm("1")]]},
        guest={(ZONE, "vm-1"): attributes(CODEX)},
    )
    scan(plain)
    assert plain.scopes == (COMPUTE_READONLY_SCOPE,)
    assert not any(url.startswith(RESOURCE_MANAGER_API) for url, _ in plain.calls)


def test_a_project_without_the_compute_api_is_counted_and_is_not_a_refusal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = org_fake(listing={"acme-dev-456": NO_COMPUTE_API})
    connector = connector_for(fake)
    with caplog.at_level(logging.INFO):
        records = scan(fake, {"organization_id": "123456789"}, connector)

    assert sorted(r.external_id for r in records) == [
        "1:codex-cli",
        "3:codex-cli",
        "4:codex-cli",
    ]
    assert connector.denied_scopes() == ()
    assert "1 without the Compute Engine API (acme-dev-456); 0 refused" in caplog.text


def test_a_listed_project_the_credential_is_refused_is_a_denied_scope_and_the_rest_are_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One project's refusal is reported and passed over; a listing that fails after
    its retries is the same with the other reason."""
    fake = org_fake(
        listing={
            "acme-dev-456": FORBIDDEN,
            "acme-old-000": FakeResponse(503, {"error": {"message": "backend"}}),
        },
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.WARNING):
        records = scan(fake, {"organization_id": "123456789"}, connector)

    assert sorted(r.external_id for r in records) == ["1:codex-cli", "3:codex-cli"]
    assert connector.denied_scopes() == (
        DeniedScope("projects/acme-dev-456", DENIED_PERMISSION),
        DeniedScope("projects/acme-old-000", DENIED_UNREACHABLE),
    )
    assert "projects/acme-dev-456: not read (permission_denied)" in caplog.text
    assert "compute.instances.list" in caplog.text
    assert "projects/acme-old-000: not read (unreachable)" in caplog.text


def test_a_named_project_the_credential_is_refused_still_ends_the_scan() -> None:
    fake = org_fake(listing={"acme-dev-456": FORBIDDEN})
    connector = connector_for(fake)
    with pytest.raises(ComputeEngineError) as exc:
        scan(
            fake,
            {"organization_id": "123456789", "project_ids": "acme-dev-456"},
            connector,
        )

    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert connector.denied_scopes() == ()


@pytest.mark.parametrize(
    "answers, code",
    [
        ({"forbidden": 4}, DiscoveryErrorCode.PERMISSION_DENIED),
        ({"forbidden": 3, "down": 1}, DiscoveryErrorCode.PROVIDER_ERROR),
    ],
    ids=["all-forbidden", "forbidden-and-unreachable"],
)
def test_refused_every_project_it_could_read_fails_the_run(
    answers: dict[str, int],
    code: DiscoveryErrorCode,
) -> None:
    """A scan allowed to read nothing is not a clean organization. A project without
    the Compute Engine API does not count as readable."""
    projects = ["acme-prod-123", "acme-dev-456", "acme-ml-789", "acme-old-000"]
    responses = [FORBIDDEN] * answers.get("forbidden", 0) + [
        FakeResponse(503, {"error": {"message": "backend"}}),
    ] * answers.get("down", 0)
    fake = org_fake(listing=dict(zip(projects, responses)))
    fake.children[ORG]["projects"].append(("acme-docs-222", "ACTIVE"))
    fake.listing["acme-docs-222"] = NO_COMPUTE_API
    connector = connector_for(fake)
    with pytest.raises(ComputeEngineError, match="refused every project") as exc:
        scan(fake, {"organization_id": "123456789"}, connector)

    assert failure_code(exc.value) is code
    assert len(connector.denied_scopes()) == 4


def test_a_refused_credential_under_a_parent_still_ends_the_scan() -> None:
    fake = org_fake(
        listing={
            "acme-prod-123": FakeResponse(
                401,
                {"error": {"code": 401, "message": "Invalid Credentials"}},
            ),
        },
    )
    with pytest.raises(ComputeEngineError) as exc:
        scan(fake, {"organization_id": "123456789"})
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_refused_resource_manager_listing_ends_the_scan() -> None:
    """The roster itself, not one project of it."""
    fake = org_fake(
        resource_manager=FakeResponse(
            403,
            {
                "error": {
                    "code": 403,
                    "message": "Permission 'resourcemanager.projects.list' denied",
                    "errors": [{"reason": "forbidden"}],
                },
            },
        ),
    )
    with pytest.raises(ComputeEngineError, match="Resource Manager") as exc:
        scan(fake, {"organization_id": "123456789"})
    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert fake.listed() == []


def test_a_parent_with_no_active_project_is_reported_not_called_clean(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeCompute(
        {},
        children={
            ORG: {"projects": [("acme-gone-111", "DELETE_REQUESTED")], "folders": []},
        },
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.WARNING):
        assert scan(fake, {"organization_id": "123456789"}, connector) == []

    assert "found no active project under organizations/123456789" in caplog.text
    assert connector.denied_scopes() == ()


def test_the_denied_scopes_reach_the_run_outcome_and_the_run_store() -> None:
    fake = org_fake(listing={"acme-dev-456": FORBIDDEN})
    connector = connector_for(fake)
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id=None,
        discovery_source_config_name="acme gce",
        discovery_source_id=None,
        vendor=VENDOR,
        job_id="job",
        scan_id=None,
        lookback_hours=24,
    )
    run_source_scan(
        FakeConfig(),  # type: ignore[arg-type]
        24,
        "workspace",
        "data-plane",
        outcome,
        connector,
        AcceptingSink(),
        LOG,
        {},
        {"organization_id": "123456789"},
    )

    assert outcome.error is None
    assert outcome.denied_scopes == [
        DeniedScope("projects/acme-dev-456", "permission_denied"),
    ]
    assert outcome.to_log_payload()["denied_scopes"] == [
        {"scope": "projects/acme-dev-456", "reason": "permission_denied"},
    ]
    body = platform_outcome(outcome)
    assert body.status == DiscoveryRunStatus.DONE
    assert [(d.scope, d.reason) for d in body.denied_scopes or []] == [
        ("projects/acme-dev-456", "permission_denied"),
    ]


class AcceptingSink:
    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: Any,
        records: Sequence[Any],
    ) -> DiscoveryPublishResult:
        return DiscoveryPublishResult(accepted=len(records))


# --- settings -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields,named",
    [
        ({}, "project_ids"),
        ({"project_ids": " , "}, "project_ids"),
        ({"organization_id": "organizations/123"}, "organizations/ or folders/ prefix"),
        ({"folder_ids": "555, my-folder"}, "'my-folder'"),
        ({"project_ids": "My Project"}, "'My Project'"),
        ({"project_ids": "acme/../other"}, "'acme/../other'"),
        ({"project_ids": PROJECT, "include_labels": "prod"}, "'prod'"),
        ({"project_ids": PROJECT, "exclude_labels": "=x"}, "'=x'"),
        ({"project_ids": PROJECT, "include_labels": "Env=prod"}, "'Env=prod'"),
    ],
)
def test_settings_that_cannot_be_scanned_fail_as_not_configured(
    fields: dict[str, str],
    named: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=named) as exc:
        settings_from(fields)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_settings_accept_several_projects_and_tidy_selectors() -> None:
    settings = settings_from(
        {
            "project_ids": f"{PROJECT}, example.com:legacy-proj, {PROJECT}",
            "include_labels": " env = prod ,owner=,env=prod",
        },
    )
    assert settings.project_ids == (PROJECT, "example.com:legacy-proj")
    assert settings.include_labels == ("env=prod", "owner=")
    assert settings.parents == ()
    assert parse_label_selectors(None, "include_labels") == ()


def test_settings_take_an_organization_or_folders_without_projects() -> None:
    settings = settings_from({"organization_id": " 123 ", "folder_ids": "555, 777"})
    assert settings.project_ids == ()
    assert settings.parents == ("organizations/123", "folders/555", "folders/777")
    assert settings.scopes == [COMPUTE_READONLY_SCOPE, CLOUD_PLATFORM_READONLY_SCOPE]


def test_a_keyless_source_needs_the_engine_to_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_ADC_ENV_VAR)
    fake = FakeCompute({PROJECT: [[vm("1")]]})
    with pytest.raises(DiscoveryConfigurationError, match=ALLOW_ADC_ENV_VAR):
        scan(fake)
    assert fake.calls == []


def test_a_key_that_cannot_be_loaded_fails_as_not_configured() -> None:
    fake = FakeCompute({PROJECT: [[vm("1")]]})
    with pytest.raises(DiscoveryConfigurationError, match="not valid JSON") as exc:
        scan(fake, credentials={"service_account_key": '{"type": "service_acc'})
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert fake.calls == []


# --- the seams ------------------------------------------------------------------------


def test_registered_with_its_secrets_declared_and_the_optional_protocols() -> None:
    assert source_connectors()[VENDOR] is ComputeEngineConnector
    connector = ComputeEngineConnector()
    assert connector.SENSITIVE_FIELDS == frozenset({"service_account_key"})
    assert isinstance(connector, ReportsDeviceCoverage)
    assert isinstance(connector, ReportsDeniedScopes)
    assert isinstance(connector, AcceptsStopCheck)
    assert connector.device_coverage() is None, "nothing read yet"
    assert connector.denied_scopes() == ()


def test_a_stop_check_ends_the_scan_after_the_vm_in_hand() -> None:
    fake = FakeCompute(
        {PROJECT: [[vm("1"), vm("2"), vm("3")]]},
        guest={(ZONE, f"vm-{i}"): attributes(CODEX) for i in "123"},
    )
    connector = connector_for(fake)
    connector.stop_when(lambda: True)
    records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["1:codex-cli"]
    assert fake.reads() == ["vm-1"]
