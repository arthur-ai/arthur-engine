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
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
import requests
import yaml
from arthur_common.models.agent_governance_schemas import (
    EndpointAgentCreationSource,
    Platform,
    RunsOn,
    SourceAddress,
)
from google.auth.exceptions import RefreshError

from discovery import source_connectors
from discovery.endpoint.gce import client as gce_client
from discovery.endpoint.gce.client import ComputeEngineError
from discovery.endpoint.gce.connector import (
    ALLOW_ADC_ENV_VAR,
    GUEST_ATTRIBUTES_DISABLED,
    READ_FAILED,
    VENDOR,
    ComputeEngineConnector,
    parse_label_selectors,
    settings_from,
)
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    ReportsDeviceCoverage,
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


def vm(
    ident: str,
    name: Optional[str] = None,
    zone: str = ZONE,
    status: str = "RUNNING",
    labels: Optional[dict[str, str]] = None,
    flag: Optional[str] = None,
    project: str = PROJECT,
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
    """Compute Engine's three read calls, and a log of what was asked.

    `pages[project]` is the listing's pages; `project_flag[project]` the project's
    `enable-guest-attributes`, absent when unset; `guest[(zone, name)]` a VM's answer,
    missing for 404, or a list of responses to hand out in turn.
    """

    def __init__(
        self,
        pages: dict[str, list[list[dict[str, Any]]]],
        project_flag: Optional[dict[str, str]] = None,
        guest: Optional[dict[tuple[str, str], Any]] = None,
        unreachables: Optional[list[str]] = None,
    ) -> None:
        self.pages = pages
        self.project_flag = {PROJECT: "TRUE"} if project_flag is None else project_flag
        self.guest = guest or {}
        self.unreachables = unreachables or []
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, params: dict[str, Any], timeout: float) -> FakeResponse:
        self.calls.append((url, dict(params)))
        path = url.removeprefix(API)
        parts = path.strip("/").split("/")

        if parts[2:] == ["aggregated", "instances"]:
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
            flag = self.project_flag.get(parts[1])
            items = [{"key": "enable-guest-attributes", "value": flag}] if flag else []
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

    def reads(self) -> list[str]:
        """The VMs whose guest attributes were read, by name."""
        return [
            url.split("/")[-2]
            for url, _ in self.calls
            if url.endswith("/getGuestAttributes")
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
    return ComputeEngineConnector(session_for=lambda creds: fake)  # type: ignore[arg-type,return-value]


def scan(
    fake: FakeCompute,
    fields: Optional[dict[str, str]] = None,
    connector: Optional[ComputeEngineConnector] = None,
) -> list[Any]:
    connector = connector or connector_for(fake)
    batches = connector.scan(FakeConfig(), 24, {}, fields or FIELDS, LOG)  # type: ignore[arg-type]
    return [record for batch in batches for record in batch]


# --- records --------------------------------------------------------------------------


def test_a_reporting_vm_is_a_linux_machine_on_gcp_addressed_by_project_zone_and_id() -> (
    None
):
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
    source = record.creation_source
    assert isinstance(source, EndpointAgentCreationSource)
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
    fake = FakeCompute(
        {
            PROJECT: [[vm("111", name="build-1")]],
            "acme-dev-456": [[vm("222", name="build-1", project="acme-dev-456")]],
        },
        project_flag={PROJECT: "TRUE", "acme-dev-456": "TRUE"},
        guest={(ZONE, "build-1"): attributes(CODEX)},
    )
    records = scan(fake, {"project_ids": f"{PROJECT}, acme-dev-456"})

    assert sorted(r.external_id for r in records) == ["111:codex-cli", "222:codex-cli"]


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
        {PROJECT: [[vm("1", status="TERMINATED")]]},
        guest={(ZONE, "vm-1"): attributes(CODEX)},
    )
    with caplog.at_level(logging.INFO):
        records = scan(fake)

    assert records[0].last_seen == datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
    assert "not running (TERMINATED: 1)" in caplog.text


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
    assert "decoded 0 of 1 VM(s)" in caplog.text
    assert "arthur-ai-discovery=enabled" in caplog.text


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
        {PROJECT: [[vm("1"), vm("2")]]},
        guest={
            (ZONE, "vm-1"): FakeResponse(500, {"error": {"message": "backend"}}),
            (ZONE, "vm-2"): attributes(CODEX),
        },
    )
    connector = connector_for(fake)
    with caplog.at_level(logging.WARNING):
        records = scan(fake, connector=connector)

    assert [r.external_id for r in records] == ["2:codex-cli"]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.unreadable_by_reason == {READ_FAILED: 1}
    assert "1: guest attributes not read" in caplog.text
    assert fake.reads().count("vm-1") == 5, "retried before giving up"


def test_a_rate_limit_sent_as_403_is_retried() -> None:
    limited = FakeResponse(
        403,
        {"error": {"code": 403, "errors": [{"reason": "rateLimitExceeded"}]}},
    )
    fake = FakeCompute(
        {PROJECT: [[vm("1")]]},
        guest={(ZONE, "vm-1"): [limited, FakeResponse(200, attributes(CODEX))]},
    )
    assert len(scan(fake)) == 1


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


# --- settings -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields,named",
    [
        ({}, "project_ids"),
        ({"project_ids": " , "}, "project_ids"),
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
    assert parse_label_selectors(None, "include_labels") == ()


def test_a_keyless_source_needs_the_engine_to_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_ADC_ENV_VAR)
    fake = FakeCompute({PROJECT: [[vm("1")]]})
    with pytest.raises(DiscoveryConfigurationError, match=ALLOW_ADC_ENV_VAR):
        scan(fake)
    assert fake.calls == []


# --- the seams ------------------------------------------------------------------------


def test_registered_with_its_secrets_declared_and_the_optional_protocols() -> None:
    assert source_connectors()[VENDOR] is ComputeEngineConnector
    connector = ComputeEngineConnector()
    assert connector.SENSITIVE_FIELDS == frozenset({"service_account_key"})
    assert isinstance(connector, ReportsDeviceCoverage)
    assert isinstance(connector, AcceptsStopCheck)
    assert connector.device_coverage() is None, "nothing read yet"


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
