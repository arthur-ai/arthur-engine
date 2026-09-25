"""Provenance persistence and assembly for discovered tasks (UP-4981 / D-09).

Provenance is what the fetch job reads back to tell the Platform where each agent was
found, so what is asserted here is that it survives the resolver intact: the source,
the address it reported, and the query where there was one. Retrieval by source and
window is covered over the wire in tests/unit/routes/tasks.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Generator

import pytest
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentCreationSource,
    AgentObservations,
    CloudAgentCreationSource,
    EndpointAgentCreationSource,
    GCPAgentCreationSource,
    ManualAgentCreationSource,
    OTELAgentCreationSource,
    ProvenanceSource,
    SIEMAgentCreationSource,
    SourceAddress,
    SourceClass,
)

from db_models import DatabaseTask, DatabaseTaskProvenanceSource
from db_models.telemetry_models import DatabaseServiceNameTaskMapping
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.task_provenance_repository import (
    TaskProvenanceRepository,
    utc_naive,
)
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import Task
from services.task.discovery_task_resolution_service import (
    DiscoveryTaskResolutionService,
)
from tests.clients.base_test_client import override_get_db_session

LAST_SEEN = datetime(2026, 9, 1, tzinfo=timezone.utc)
SPLUNK_QUERY = "index=proxy sourcetype=zscaler dest_host=*openai.com | stats by user"


@pytest.fixture
def db_session():
    session = override_get_db_session()
    yield session
    session.close()


@pytest.fixture
def task_repo(db_session) -> TaskRepository:
    return TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        get_application_config(session=db_session),
    )


@pytest.fixture
def resolver(db_session, task_repo) -> DiscoveryTaskResolutionService:
    return DiscoveryTaskResolutionService(db_session, task_repo)


@pytest.fixture
def provenance_repo(db_session) -> TaskProvenanceRepository:
    return TaskProvenanceRepository(db_session)


@pytest.fixture
def tracked_tasks(db_session) -> Generator[list[str], None, None]:
    """Task IDs to delete, with their mappings and provenance, when the test finishes."""
    task_ids: list[str] = []
    yield task_ids

    if task_ids:
        db_session.query(DatabaseTaskProvenanceSource).filter(
            DatabaseTaskProvenanceSource.task_id.in_(task_ids),
        ).delete(synchronize_session=False)
        db_session.query(DatabaseServiceNameTaskMapping).filter(
            DatabaseServiceNameTaskMapping.task_id.in_(task_ids),
        ).delete(synchronize_session=False)
        db_session.query(DatabaseTask).filter(
            DatabaseTask.id.in_(task_ids),
        ).delete(synchronize_session=False)
        db_session.commit()


def _run_id() -> str:
    return uuid.uuid4().hex[:8]


def _siem_record(
    external_id: str,
    service_names: tuple[str, ...] = (),
) -> DiscoveredAgentRecord:
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=external_id,
        last_seen=LAST_SEEN,
        creation_source=SIEMAgentCreationSource(
            vendor="splunk_enterprise",
            address=SourceAddress(
                instance="splunk-prod",
                scope="index=proxy",
                resource_id=external_id,
                query=SPLUNK_QUERY,
            ),
            observations=AgentObservations(service_names=list(service_names)),
        ),
    )


def _cloud_record(
    external_id: str,
    vendor: str,
    instance: str,
    region: str,
) -> DiscoveredAgentRecord:
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=external_id,
        last_seen=LAST_SEEN,
        creation_source=CloudAgentCreationSource(
            vendor=vendor,
            address=SourceAddress(
                instance=instance,
                scope=region,
                resource_id=external_id,
            ),
        ),
    )


def _endpoint_record(
    external_id: str,
    device: str,
    service_names: tuple[str, ...] = (),
) -> DiscoveredAgentRecord:
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=external_id,
        last_seen=LAST_SEEN,
        creation_source=EndpointAgentCreationSource(
            vendor="jamf_pro",
            address=SourceAddress(
                instance=f"serial:{device}",
                resource_kind="app",
                resource_id="openclaw",
            ),
            observations=AgentObservations(service_names=list(service_names)),
        ),
    )


def _served_provenance(task_repo: TaskRepository, task_id: str):
    """The provenance the agent-tasks endpoint would serve for one task."""
    db_task = task_repo.get_db_task_by_id(task_id, include_archived=True)
    task = Task._from_database_model(db_task)
    rows = TaskProvenanceRepository(task_repo.db_session).get_by_task_ids([task_id])
    return task_repo._get_task_provenance(
        task_repo._get_task_creation_source(task),
        rows.get(task_id, []),
    )


def _rows(db_session, task_id: str) -> list[DatabaseTaskProvenanceSource]:
    db_session.expire_all()
    return (
        db_session.query(DatabaseTaskProvenanceSource)
        .filter(DatabaseTaskProvenanceSource.task_id == task_id)
        .all()
    )


@pytest.mark.unit_tests
def test_siem_finding_carries_its_instance_and_query(
    resolver,
    task_repo,
    tracked_tasks,
):
    source_id = uuid.uuid4()
    external_id = f"{_run_id()}-siem"

    [resolved] = resolver.resolve_records(
        [_siem_record(external_id)],
        source_id=source_id,
    ).resolved
    tracked_tasks.append(resolved.task_id)

    provenance = _served_provenance(task_repo, resolved.task_id)
    [entry] = provenance.sources
    assert entry.source_id == source_id
    assert entry.source_class is SourceClass.SIEM
    assert entry.vendor == "splunk_enterprise"
    assert entry.address.instance == "splunk-prod"
    assert entry.address.query == SPLUNK_QUERY
    assert provenance.source_classes == [SourceClass.SIEM]


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("vendor", "instance"),
    [
        # A Bedrock finding: the AWS account, and the agent's ID within it.
        ("aws_bedrock", "123456789012"),
        # A Vertex finding: the GCP project, and the reasoning engine's ID within it.
        ("gcp_vertex", "arthur-prod-project"),
    ],
)
def test_cloud_finding_carries_its_account_and_resource(
    resolver,
    task_repo,
    tracked_tasks,
    vendor,
    instance,
):
    source_id = uuid.uuid4()
    external_id = f"{_run_id()}-{vendor}-agent"

    [resolved] = resolver.resolve_records(
        [_cloud_record(external_id, vendor, instance, "us-east1")],
        source_id=source_id,
    ).resolved
    tracked_tasks.append(resolved.task_id)

    [entry] = _served_provenance(task_repo, resolved.task_id).sources
    assert entry.source_id == source_id
    assert entry.source_class is SourceClass.CLOUD
    assert entry.vendor == vendor
    assert entry.address.instance == instance
    assert entry.address.scope == "us-east1"
    assert entry.address.resource_id == external_id


@pytest.mark.unit_tests
def test_rescan_updates_the_report_rather_than_adding_one(
    resolver,
    provenance_repo,
    db_session,
    tracked_tasks,
):
    """A source that reports the same agent every scan holds one row, kept current."""
    source_id = uuid.uuid4()
    external_id = f"{_run_id()}-siem"

    [first] = resolver.resolve_records(
        [_siem_record(external_id)],
        source_id=source_id,
    ).resolved
    tracked_tasks.append(first.task_id)
    [row] = _rows(db_session, first.task_id)
    first_reported_at = row.first_reported_at

    # Pretend the first scan ran an hour ago, so the re-scan's timestamp is
    # distinguishable from it without sleeping.
    row.first_reported_at = row.last_reported_at = first_reported_at - timedelta(
        hours=1,
    )
    db_session.commit()

    [second] = resolver.resolve_records(
        [_siem_record(external_id)],
        source_id=source_id,
    ).resolved
    assert second.task_id == first.task_id

    [row] = _rows(db_session, first.task_id)
    assert row.first_reported_at == first_reported_at - timedelta(hours=1)
    assert row.last_reported_at > row.first_reported_at


@pytest.mark.unit_tests
def test_every_address_a_source_reports_is_kept(
    resolver,
    task_repo,
    tracked_tasks,
):
    """One agent on three devices, converging through a service name, is three entries.

    This is the unbounded list the joined table exists to hold: the address differs per
    device, so collapsing to one entry per source would keep one device and lose the
    rest.
    """
    run = _run_id()
    service_name = f"{run}-openclaw"
    records = [
        _endpoint_record(f"{run}-device-{i}", f"DEVICE{i}", (service_name,))
        for i in range(3)
    ]

    resolved = resolver.resolve_records(records, source_id=uuid.uuid4()).resolved
    tracked_tasks.extend({r.task_id for r in resolved})
    assert len({r.task_id for r in resolved}) == 1

    provenance = _served_provenance(task_repo, resolved[0].task_id)
    assert sorted(entry.address.instance for entry in provenance.sources) == [
        "serial:DEVICE0",
        "serial:DEVICE1",
        "serial:DEVICE2",
    ]
    assert provenance.source_classes == [SourceClass.ENDPOINT]


@pytest.mark.unit_tests
def test_two_sources_reporting_one_agent_both_appear(
    resolver,
    task_repo,
    tracked_tasks,
):
    """Corroboration: a SIEM and an endpoint source converge on one task via a name."""
    run = _run_id()
    service_name = f"{run}-checkout-agent"
    siem_source, endpoint_source = uuid.uuid4(), uuid.uuid4()

    [from_siem] = resolver.resolve_records(
        [_siem_record(f"{run}-siem", (service_name,))],
        source_id=siem_source,
    ).resolved
    [from_endpoint] = resolver.resolve_records(
        [_endpoint_record(f"{run}-endpoint", "DEVICE0", (service_name,))],
        source_id=endpoint_source,
    ).resolved
    tracked_tasks.append(from_siem.task_id)
    assert from_endpoint.task_id == from_siem.task_id

    provenance = _served_provenance(task_repo, from_siem.task_id)
    assert {entry.source_id for entry in provenance.sources} == {
        siem_source,
        endpoint_source,
    }
    assert set(provenance.source_classes) == {SourceClass.SIEM, SourceClass.ENDPOINT}


@pytest.mark.unit_tests
def test_failed_record_leaves_no_provenance(
    resolver,
    db_session,
    tracked_tasks,
):
    """A record that did not resolve names a task that is not there to hold it."""
    missing_task_id = str(uuid.uuid4())
    record = _siem_record(f"{_run_id()}-bad").model_copy(
        update={"task_id": missing_task_id},
    )

    outcome = resolver.resolve_records([record], source_id=uuid.uuid4())

    assert outcome.resolved == []
    assert len(outcome.failed) == 1
    assert _rows(db_session, missing_task_id) == []


@pytest.mark.unit_tests
def test_duplicate_key_in_one_batch_is_recorded_once(
    provenance_repo,
    resolver,
    db_session,
    tracked_tasks,
):
    """One statement cannot upsert a row twice, so the batch is deduplicated first."""
    external_id = f"{_run_id()}-siem"
    resolved = resolver.resolve_records(
        [_siem_record(external_id), _siem_record(external_id)],
        source_id=uuid.uuid4(),
    ).resolved
    tracked_tasks.append(resolved[0].task_id)

    assert len(_rows(db_session, resolved[0].task_id)) == 1


@pytest.mark.unit_tests
def test_report_without_a_source_is_refused(provenance_repo):
    entry = ProvenanceSource.from_creation_source(
        _siem_record("x").task_creation_source,
    )

    with pytest.raises(ValueError, match="no source_id"):
        provenance_repo.record_reports([("x", str(uuid.uuid4()), entry)])


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("creation_source", "source_class"),
    [
        (OTELAgentCreationSource(service_names=["checkout"]), SourceClass.OTEL),
        (ManualAgentCreationSource(), SourceClass.MANUAL),
        (
            GCPAgentCreationSource(
                gcp_project_id="proj",
                gcp_region="us-central1",
                gcp_reasoning_engine_id="engine-1",
            ),
            SourceClass.CLOUD,
        ),
    ],
)
def test_task_never_reported_by_a_source_takes_provenance_from_its_creation(
    creation_source,
    source_class,
):
    """OTEL, manual and legacy GCP tasks have no rows, and still have provenance."""
    provenance = TaskRepository._get_task_provenance(
        AgentCreationSource(root=creation_source),
        [],
    )

    [entry] = provenance.sources
    assert entry.source_class is source_class
    assert entry.source_id is None


@pytest.mark.unit_tests
def test_otel_task_later_discovered_keeps_both_entries():
    """Traces made the task; a scan found it again. Both are how it is known."""
    source_id = uuid.uuid4()
    row = DatabaseTaskProvenanceSource(
        source_id=source_id,
        external_id="splunk-1",
        task_id=str(uuid.uuid4()),
        source_class=SourceClass.SIEM,
        vendor="splunk_enterprise",
        address={"instance": "splunk-prod", "resource_id": "splunk-1"},
        first_reported_at=datetime(2026, 9, 1),
        last_reported_at=datetime(2026, 9, 1),
    )

    provenance = TaskRepository._get_task_provenance(
        AgentCreationSource(root=OTELAgentCreationSource()),
        [row],
    )

    assert [entry.source_class for entry in provenance.sources] == [
        SourceClass.OTEL,
        SourceClass.SIEM,
    ]
    assert provenance.sources[1].source_id == source_id


@pytest.mark.unit_tests
def test_discovered_task_is_represented_by_its_rows_not_twice():
    """The scan that minted a task is already its row, which also names the source."""
    record = _siem_record("splunk-1")
    row = DatabaseTaskProvenanceSource(
        source_id=uuid.uuid4(),
        external_id="splunk-1",
        task_id=str(uuid.uuid4()),
        source_class=SourceClass.SIEM,
        vendor="splunk_enterprise",
        address=record.creation_source.address.model_dump(mode="json"),
        first_reported_at=datetime(2026, 9, 1),
        last_reported_at=datetime(2026, 9, 1),
    )

    with_rows = TaskRepository._get_task_provenance(
        record.task_creation_source,
        [row],
    )
    without_rows = TaskRepository._get_task_provenance(
        record.task_creation_source,
        [],
    )

    assert [entry.source_id for entry in with_rows.sources] == [row.source_id]
    # A discovered task with nothing stored still says what found it.
    [fallback] = without_rows.sources
    assert fallback.source_class is SourceClass.SIEM
    assert fallback.source_id is None


@pytest.mark.unit_tests
def test_minting_source_survives_another_source_converging_on_the_task():
    """A task minted with no row of its own keeps its finding once others report it.

    Tasks minted before rows were written, or whose minting scan failed to record its
    report, have no row for the source that found them. A second source resolving to
    the task later must not erase the first.
    """
    record = _siem_record("splunk-1")
    other = DatabaseTaskProvenanceSource(
        source_id=uuid.uuid4(),
        external_id="elastic-1",
        task_id=str(uuid.uuid4()),
        source_class=SourceClass.SIEM,
        vendor="elastic_cloud",
        address={"instance": "elastic-prod", "resource_id": "elastic-1"},
        first_reported_at=datetime(2026, 9, 1),
        last_reported_at=datetime(2026, 9, 1),
    )

    provenance = TaskRepository._get_task_provenance(
        record.task_creation_source,
        [other],
    )

    assert [(entry.vendor, entry.source_id) for entry in provenance.sources] == [
        ("splunk_enterprise", None),
        ("elastic_cloud", other.source_id),
    ]


@pytest.mark.unit_tests
def test_minting_row_still_stands_in_after_its_query_is_edited():
    """The row holds the latest scan's query; the finding still matches it."""
    record = _siem_record("splunk-1")
    address = record.creation_source.address.model_dump(mode="json")
    row = DatabaseTaskProvenanceSource(
        source_id=uuid.uuid4(),
        external_id="splunk-1",
        task_id=str(uuid.uuid4()),
        source_class=SourceClass.SIEM,
        vendor="splunk_enterprise",
        address={**address, "query": "search index=proxy | head 10"},
        first_reported_at=datetime(2026, 9, 1),
        last_reported_at=datetime(2026, 9, 2),
    )

    provenance = TaskRepository._get_task_provenance(
        record.task_creation_source,
        [row],
    )

    assert [entry.source_id for entry in provenance.sources] == [row.source_id]


@pytest.mark.unit_tests
def test_task_with_nothing_to_say_has_no_provenance():
    assert TaskRepository._get_task_provenance(None, []) is None


@pytest.mark.unit_tests
def test_utc_naive_converts_offsets_and_trusts_naive_input():
    moment = datetime(2026, 9, 23, 14, 0, tzinfo=timezone(timedelta(hours=-4)))

    assert utc_naive(moment) == datetime(2026, 9, 23, 18, 0)
    assert utc_naive(datetime(2026, 9, 23, 18, 0)) == datetime(2026, 9, 23, 18, 0)
