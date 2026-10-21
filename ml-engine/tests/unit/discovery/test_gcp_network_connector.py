"""GCP network logs (gcp_network): Cloud DNS lookups and serverless flows to records.

The fixture is real Cloud DNS and VPC flow entries from a demo project, with the
project id and number replaced. In it:
- a VM called api.openai.com and Vertex AI;
- the Cloud Run job `arthur-scn-run` called api.openai.com;
- a control job called only example.com;
- a job `arthur-scn-once` called api.openai.com once.
Cloud Run's own DNS lookups carry no source fields, so the jobs are named by their flow
records.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import NetworkAgentCreationSource
from google.auth.credentials import Credentials

from discovery import source_connectors
from discovery.network.gcp_logging.client import (
    LoggingReadError,
    dns_filter,
    serverless_flow_filter,
)
from discovery.network.gcp_logging.connector import (
    VENDOR,
    GcpNetworkConnector,
    settings_from,
)
from discovery.network.gcp_logging.records import NetworkFold, _answer_addresses
from discovery.network.hosts import DestinationMatcher
from job_executors.discovery_scan import DiscoveryConfigurationError

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "gcp_network_entries.json").read_text()
)
NOW = datetime(2026, 10, 21, 0, 30, tzinfo=timezone.utc)
LOG = logging.getLogger("test.gcp_network")
JOBS = {"us-east4": {"arthur-scn-run", "arthur-scn-control", "arthur-scn-once"}}


class FakeLogs:
    def __init__(
        self,
        dns: Iterable[dict[str, Any]] = FIXTURE["dns"],
        flows: Iterable[dict[str, Any]] = FIXTURE["flows"],
        jobs: Optional[dict[str, set[str]]] = None,
        jobs_error: Optional[Exception] = None,
    ) -> None:
        self.dns, self.flows = list(dns), list(flows)
        self.jobs = JOBS if jobs is None else jobs
        self.jobs_error = jobs_error
        self.filters: list[str] = []

    def __call__(self, credentials: Optional[Credentials]) -> "FakeLogs":
        return self

    def entries(self, project_id: str, log_filter: str) -> Iterable[dict[str, Any]]:
        self.filters.append(log_filter)
        return self.dns if "dns_queries" in log_filter else self.flows

    def run_jobs(self, project_id: str, region: str) -> set[str]:
        if self.jobs_error is not None:
            raise self.jobs_error
        return self.jobs.get(region, set())


def scan(logs: FakeLogs, fields: Optional[dict[str, str]] = None) -> list[Any]:
    connector = GcpNetworkConnector(logs=logs, clock=lambda: NOW)  # type: ignore[arg-type]
    config = DiscoverySourceConfigSpec.model_construct(
        name="gcp", vendor=VENDOR, query=None
    )
    out: list[Any] = []
    for batch in connector.scan(
        config, 2, {}, fields or {"project_id": "demo-project"}, LOG
    ):
        out.extend(batch)
    return out


@pytest.fixture(autouse=True)
def allow_adc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARTHUR_ENGINE_GCP_NETWORK_ALLOW_ADC", "true")


def by_id(records: list[Any]) -> dict[str, Any]:
    return {r.creation_source.address.resource_id: r for r in records}


def test_a_vm_is_named_by_its_own_dns_lookups() -> None:
    vms = [
        r
        for r in scan(FakeLogs())
        if r.creation_source.address.resource_kind == "instance"
    ]
    assert vms, "the VM's lookups name it"
    vm = vms[0]
    source = vm.creation_source
    assert isinstance(source, NetworkAgentCreationSource)
    assert source.address.instance == source.address.resource_id
    assert source.address.scope == "demo-project/us-east4-a"
    assert source.observations.host_name == "arthur-scn-vm"
    assert {d.host for d in source.destinations} == {
        "api.openai.com",
        "us-central1-aiplatform.googleapis.com",
    }


def test_a_cloud_run_job_is_named_by_its_flows_and_folded_into_its_job() -> None:
    records = by_id(scan(FakeLogs()))
    job = records["run/jobs/arthur-scn-run"]
    address = job.creation_source.address
    assert (address.resource_kind, address.instance, address.scope) == (
        "workload",
        "run/jobs/arthur-scn-run",
        "demo-project/us-east4",
    )
    # The job also called Vertex AI; in this small sample its address answered for
    # nothing else, so it is labelled (see the shared-address test for the rule).
    assert "api.openai.com" in {d.host for d in job.creation_source.destinations}
    assert job.external_id == "demo-project/us-east4/workload/run/jobs/arthur-scn-run"
    assert "run/jobs/arthur-scn-once" in records


def test_a_job_calling_no_ai_host_is_not_a_record() -> None:
    assert not any("control" in key for key in by_id(scan(FakeLogs())))


def test_without_the_job_list_an_execution_keeps_its_own_name(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        records = by_id(scan(FakeLogs(jobs_error=LoggingReadError(403, "denied"))))
    assert any(k.startswith("run/jobs/arthur-scn-run-") for k in records)
    assert "roles/run.viewer" in caplog.text


def test_an_address_shared_with_a_host_that_is_not_inference_is_skipped() -> None:
    """Google's front ends answer for every googleapis.com host, so a flow to one
    cannot say Vertex was called."""
    shared = "172.217.114.4"
    dns = [
        {
            "timestamp": "2026-10-20T23:40:00Z",
            "jsonPayload": {
                "queryName": "us-central1-aiplatform.googleapis.com.",
                "responseCode": "NOERROR",
                "rdata": f"us-central1-aiplatform.googleapis.com.\t300\tIN\ta\t{shared}",
            },
        },
        {
            "timestamp": "2026-10-20T23:40:00Z",
            "jsonPayload": {
                "queryName": "logging.googleapis.com.",
                "responseCode": "NOERROR",
                "rdata": f"logging.googleapis.com.\t300\tIN\ta\t{shared}",
            },
        },
    ]
    flow = {
        "timestamp": "2026-10-20T23:41:00Z",
        "jsonPayload": {
            "connection": {"dest_ip": shared, "dest_port": 443},
            "src_serverless_details": {
                "project_id": "demo-project",
                "region": "us-east4",
                "cloud_run_job_details": {"job_name": "arthur-scn-run-abc12"},
            },
        },
    }
    fold = NetworkFold(DestinationMatcher(), lambda region: JOBS[region])
    for entry in dns:
        fold.lookup(entry)
    fold.flow(flow)
    assert fold.records(VENDOR) == []
    assert fold.counts.ambiguous_flows == 1


def test_rdata_addresses_are_read_and_a_cut_line_is_skipped() -> None:
    rdata = (
        "api.openai.com.\t60\tIN\ta\t162.159.140.245\n"
        "api.openai.com.\t60\tIN\taaaa\t2606:4700:7::f3\n"
        "api.openai.com.\t60\tI..."
    )
    assert _answer_addresses(rdata) == {"162.159.140.245", "2606:4700:7::f3"}


def test_the_filters_read_answered_lookups_and_serverless_flows_only() -> None:
    since = datetime(2026, 10, 20, 22, 30, tzinfo=timezone.utc)
    assert 'jsonPayload.responseCode="NOERROR"' in dns_filter("p", since)
    assert "dns.googleapis.com%2Fdns_queries" in dns_filter("p", since)
    flow = serverless_flow_filter("p", since)
    assert "compute.googleapis.com%2Fvpc_flows" in flow
    assert "jsonPayload.src_serverless_details:*" in flow


def test_no_dns_lookups_names_the_likely_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        assert scan(FakeLogs(dns=[], flows=[])) == []
    assert "DNS server policy" in caplog.text


def test_a_missing_project_is_named() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="project_id"):
        settings_from({})


def test_extra_hosts_follow_the_aws_network_rules() -> None:
    settings = settings_from(
        {"project_id": "p", "extra_inference_hosts": "LLM.internal.example.com."}
    )
    assert settings.extra_inference_hosts == ("llm.internal.example.com",)


def test_the_connector_is_registered() -> None:
    assert source_connectors()[VENDOR] is GcpNetworkConnector
    assert GcpNetworkConnector.SENSITIVE_FIELDS == frozenset({"service_account_key"})
