"""How events become rows of the CSV file destination, and how the file is kept."""

import csv
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import (
    DiscoveredAgentRecord,
    DiscoveryOutputRecord,
)
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    CloudAgentCreationSource,
    DataSource,
    IdentityBasis,
    LLMModel,
    NetworkAgentCreationSource,
    NetworkDestination,
    RunsOn,
    SourceAddress,
    SubAgent,
    Tool,
)

from job_executors.discovery_scan import DiscoveryScanOutcome
from standalone.config_values import BASE_DIR_CONTEXT
from standalone.sinks.common import (
    SinkDeliveryError,
    discovered_agent_event,
    scan_outcome_event,
)
from standalone.sinks.csv_file import COLUMNS, CsvDestination, CsvSink

LOG = logging.getLogger("sinks-csv-file-test")
OBSERVED_AT = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
LAST_SEEN = datetime(2026, 10, 7, 11, 0, tzinfo=timezone.utc)
SOURCE_ID = "11111111-1111-1111-1111-111111111111"


def config(vendor: str = "jamf_pro") -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name="all-hosts",
        vendor=vendor,
        query="",
        query_language="none",
        lookback_window_seconds=86400,
    )


def event(record: DiscoveryOutputRecord, vendor: str = "jamf_pro") -> dict[str, Any]:
    return discovered_agent_event(record, config(vendor), "corp", OBSERVED_AT)


def plain(external_id: str, name: str = "") -> dict[str, Any]:
    return event(
        DiscoveryOutputRecord(
            external_id=external_id,
            name=name or f"agent-{external_id}",
            last_seen=LAST_SEEN,
        ),
    )


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def lines(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def write(path: Path, *events: dict[str, Any]) -> None:
    sink = CsvSink(path, LOG)
    try:
        sink.send(list(events))
    finally:
        sink.close()


def test_the_header_is_written_once_and_rows_are_appended(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    sink = CsvSink(path, LOG)

    sink.send([plain("a"), plain("b")])
    sink.send([plain("c")])
    sink.close()

    header, *body = lines(path)
    assert tuple(header) == COLUMNS
    assert [row[COLUMNS.index("external_id")] for row in body] == ["a", "b", "c"]


def test_a_restarted_engine_appends_to_the_same_file(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"

    write(path, plain("a"))
    write(path, plain("a"))

    assert [r["external_id"] for r in rows(path)] == ["a", "a"]
    assert sum(1 for line in lines(path) if tuple(line) == COLUMNS) == 1


def test_a_row_cut_off_mid_write_does_not_swallow_the_next(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    write(path, plain("a"))
    # As a full disk or a kill during a flush leaves it: the last row half written.
    data = path.read_bytes()
    path.write_bytes(data[: len(data) - 40])

    write(path, plain("b"))

    header, cut, last = lines(path)
    assert cut[COLUMNS.index("external_id")] == "a"
    assert tuple(header) == COLUMNS
    assert dict(zip(COLUMNS, last))["external_id"] == "b"
    assert len(last) == len(COLUMNS)


def test_an_empty_file_gets_the_header(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    path.touch()

    write(path, plain("a"))

    assert tuple(lines(path)[0]) == COLUMNS


def test_the_parent_directory_is_created(tmp_path: Path) -> None:
    path = tmp_path / "out" / "nested" / "agents.csv"

    write(path, plain("a"))

    assert [r["external_id"] for r in rows(path)] == ["a"]


def test_a_file_with_another_header_stops_the_engine(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    path.write_text("id,name\n1,x\n", encoding="utf-8")

    with pytest.raises(ValueError, match="header"):
        CsvSink(path, LOG)

    assert path.read_text(encoding="utf-8") == "id,name\n1,x\n"


def test_a_path_that_cannot_be_opened_stops_the_engine(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Cannot write the csv destination"):
        CsvSink(tmp_path, LOG)


def test_a_cloud_record_is_spread_over_its_columns(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    record = DiscoveredAgentRecord(
        external_id="projects/1/locations/us-central1/reasoningEngines/9",
        name="assistant",
        last_seen=LAST_SEEN,
        runs_on=RunsOn.GCP,
        task_id="task-1",
        llm_models=[LLMModel(name="gemini-2.5-pro")],
        tools=[Tool(name="search", arguments=[]), Tool(name="calendar", arguments=[])],
        sub_agents=[SubAgent(name="planner")],
        data_sources=[DataSource(url="gs://bucket/docs"), DataSource(url="bq://t")],
        creation_source=CloudAgentCreationSource(
            vendor="gcp_vertex",
            address=SourceAddress(
                instance="acme-prod",
                scope="us-central1",
                resource_kind="reasoning_engine",
                resource_id="9",
            ),
            observations=AgentObservations(
                version="1.2",
                classification="Cloud agent",
                permissions=["aiplatform.user", "storage.read"],
                service_names=["assistant-svc"],
            ),
        ),
    )

    write(path, event(record, vendor="gcp_vertex"))

    (row,) = rows(path)
    assert row == {
        "observed_at": OBSERVED_AT.isoformat(),
        "source_id": SOURCE_ID,
        "source_name": "corp",
        "source_vendor": "gcp_vertex",
        "source_config_name": "all-hosts",
        "external_id": "projects/1/locations/us-central1/reasoningEngines/9",
        "name": "assistant",
        "last_seen": "2026-10-07T11:00:00Z",
        "runs_on": "gcp",
        "platform": "",
        "task_id": "task-1",
        "creation_source_type": "CLOUD",
        "creation_source_vendor": "gcp_vertex",
        "address_instance": "acme-prod",
        "address_scope": "us-central1",
        "address_resource_kind": "reasoning_engine",
        "address_resource_id": "9",
        "host_name": "",
        "host_group": "",
        "os_version": "",
        "assigned_user": "",
        "install_path": "",
        "version": "1.2",
        "classification": "Cloud agent",
        "llm_models": "gemini-2.5-pro",
        "tools": "search; calendar",
        "sub_agents": "planner",
        "data_sources": "gs://bucket/docs; bq://t",
        "network_destinations": "",
        "identity_basis": "",
        "permissions": "aiplatform.user; storage.read",
        "service_names": "assistant-svc",
    }


def test_a_network_host_record_lists_its_destination_hosts(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    record = DiscoveredAgentRecord(
        external_id="i-0abc",
        name="i-0abc calling OpenAI, Anthropic",
        last_seen=LAST_SEEN,
        runs_on=RunsOn.AWS,
        creation_source=NetworkAgentCreationSource(
            vendor="aws_network",
            address=SourceAddress(
                instance="i-0abc",
                scope="123456789012/us-east-1",
                resource_kind="instance",
                resource_id="i-0abc",
            ),
            observations=AgentObservations(host_name="i-0abc", host_group="vpc-1"),
            destinations=[
                NetworkDestination(host="api.openai.com", provider="openai"),
                NetworkDestination(host="api.anthropic.com", provider="anthropic"),
            ],
        ),
    )

    write(path, event(record, vendor="aws_network"))

    (row,) = rows(path)
    assert row["creation_source_type"] == "NETWORK"
    assert row["address_scope"] == "123456789012/us-east-1"
    assert row["address_resource_kind"] == "instance"
    assert row["host_name"] == "i-0abc" and row["host_group"] == "vpc-1"
    assert row["network_destinations"] == "api.openai.com; api.anthropic.com"
    # Not reported by a network source, so empty rather than "none".
    assert row["tools"] == "" and row["llm_models"] == ""
    assert row["identity_basis"] == ""


def test_a_gateway_caller_record_carries_its_identity_basis(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    record = DiscoveredAgentRecord(
        external_id="litellm:vk:abc",
        name="support-bot",
        last_seen=LAST_SEEN,
        llm_models=[LLMModel(name="gpt-4o"), LLMModel(name="gpt-4o-mini")],
        creation_source=NetworkAgentCreationSource(
            vendor="litellm",
            address=SourceAddress(
                instance="proxy.example.com",
                resource_kind="virtual_key",
                resource_id="hash123",
            ),
            identity_basis=IdentityBasis.CREDENTIAL,
            observations=AgentObservations(host_group="team-a"),
        ),
    )

    write(path, event(record, vendor="litellm"))

    (row,) = rows(path)
    assert row["identity_basis"] == "credential"
    assert row["llm_models"] == "gpt-4o; gpt-4o-mini"
    assert row["network_destinations"] == ""


def test_scan_outcomes_are_not_written(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id="cfg",
        discovery_source_config_name="all-hosts",
        discovery_source_id=SOURCE_ID,
        vendor="jamf_pro",
        job_id="local",
        scan_id=None,
        lookback_hours=24,
    )
    sink = CsvSink(path, LOG)

    refused = sink.send([plain("a"), scan_outcome_event(outcome, "corp")])
    sink.send([scan_outcome_event(outcome, "corp")])
    sink.close()

    assert not refused
    assert [r["external_id"] for r in rows(path)] == ["a"]


@pytest.mark.parametrize(
    "name",
    ['=HYPERLINK("http://x")', "+1", "-cmd", "@SUM(A1)", "\tx", "\rx"],
)
def test_a_cell_a_spreadsheet_would_run_is_quoted_as_text(
    tmp_path: Path,
    name: str,
) -> None:
    path = tmp_path / "agents.csv"

    write(path, plain("a", name=name))

    (row,) = rows(path)
    assert row["name"] == f"'{name}"


def test_commas_quotes_and_newlines_survive(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    name = 'agent, "quoted"\nsecond line — ünïcode'

    write(path, plain("a", name=name))

    (row,) = rows(path)
    assert row["name"] == name


def test_a_failed_write_fails_the_batch(tmp_path: Path) -> None:
    sink = CsvSink(tmp_path / "agents.csv", LOG)

    class FullDisk:
        def writerows(self, rows: Any) -> None:
            raise OSError(28, "No space left on device")

    sink._writer = FullDisk()  # type: ignore[assignment]

    with pytest.raises(SinkDeliveryError, match="No space left on device"):
        sink.send([plain("a")])
    sink.close()


def test_concurrent_scans_write_whole_rows(tmp_path: Path) -> None:
    path = tmp_path / "agents.csv"
    sink = CsvSink(path, LOG)
    long_name = "x" * 5000

    def scan(n: int) -> None:
        for batch in range(20):
            sink.send([plain(f"{n}-{batch}-{i}", name=long_name) for i in range(10)])

    threads = [threading.Thread(target=scan, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    sink.close()

    written = rows(path)
    assert len(written) == 8 * 20 * 10
    assert len({r["external_id"] for r in written}) == len(written)
    assert all(r["name"] == long_name for r in written)
    assert all(None not in r for r in written)


def test_a_relative_path_resolves_beside_the_config(tmp_path: Path) -> None:
    destination = CsvDestination.model_validate(
        {"type": "csv", "path": "out/agents.csv"},
        context={BASE_DIR_CONTEXT: tmp_path},
    )

    assert destination.path == str(tmp_path / "out" / "agents.csv")


def test_the_destination_builds_its_sink(tmp_path: Path) -> None:
    destination = CsvDestination(type="csv", path=str(tmp_path / "agents.csv"))

    sink = destination.build_sink(LOG)

    assert isinstance(sink, CsvSink)
    assert sink.secrets() == ()
    sink.close()
