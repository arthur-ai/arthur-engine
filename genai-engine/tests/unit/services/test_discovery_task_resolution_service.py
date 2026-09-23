"""Resolution of discovered records to tasks (UP-4980 / D-08).

These tests are the identity guarantee for agentic discovery. Everything downstream --
the fetch job, the inventory, coverage counts, triage -- operates on whatever tasks
this step produced, and none of it can correct a bad key afterwards, so the scale case
is tested at the scale it has to work at rather than with two rows.
"""

import uuid
from datetime import datetime, timezone
from typing import Generator, Iterable

import pytest
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    EndpointAgentCreationSource,
    OTELAgentCreationSource,
    SIEMAgentCreationSource,
    SourceAddress,
)
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from db_models import DatabaseTask
from db_models.telemetry_models import DatabaseServiceNameTaskMapping
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from repositories.tasks_repository import TaskRepository
from schemas.agent_discovery_schemas import (
    DiscoveredRecordFailureReason,
    TaskResolutionMethod,
)
from schemas.enums import MappingKeyKind
from services.task.discovery_task_resolution_service import (
    DiscoveryTaskResolutionService,
)
from services.trace.trace_ingestion_service import TraceIngestionService
from tests.clients.base_test_client import override_get_db_session

# Every record carries the time its source last saw the agent. Resolution does not read
# it, so one fixed instant keeps it out of the way of what these tests are about.
LAST_SEEN = datetime(2026, 9, 1, tzinfo=timezone.utc)


@pytest.fixture
def db_session():
    session = override_get_db_session()
    yield session
    session.close()


@pytest.fixture
def resolver(db_session) -> DiscoveryTaskResolutionService:
    task_repo = TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        get_application_config(session=db_session),
    )
    return DiscoveryTaskResolutionService(db_session, task_repo)


@pytest.fixture
def tracked_tasks(db_session) -> Generator[list[str], None, None]:
    """Task IDs to delete, with their mappings, when the test finishes."""
    task_ids: list[str] = []
    yield task_ids

    if task_ids:
        db_session.query(DatabaseServiceNameTaskMapping).filter(
            DatabaseServiceNameTaskMapping.task_id.in_(task_ids),
        ).delete(synchronize_session=False)
        db_session.query(DatabaseTask).filter(
            DatabaseTask.id.in_(task_ids),
        ).delete(synchronize_session=False)
        db_session.commit()


def _run_id() -> str:
    """A prefix unique to one test, since the mapping table is keyed on the name."""
    return uuid.uuid4().hex[:8]


def _endpoint_record(
    external_id: str,
    name: str | None = None,
    service_names: Iterable[str] = (),
    device: str = "C02XL4KHQ6NV",
    task_id: str | None = None,
) -> DiscoveredAgentRecord:
    """A Jamf finding: one agent on one managed device."""
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=name or external_id,
        last_seen=LAST_SEEN,
        task_id=task_id,
        creation_source=EndpointAgentCreationSource(
            vendor="jamf_pro",
            address=SourceAddress(
                instance=f"serial:{device}",
                resource_kind="app",
                resource_id=external_id,
            ),
            observations=AgentObservations(service_names=list(service_names)),
        ),
    )


def _siem_record(
    external_id: str,
    name: str | None = None,
    service_names: Iterable[str] = (),
    instance: str = "splunk-prod",
) -> DiscoveredAgentRecord:
    """A finding surfaced by a query against the customer's security stack."""
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=name or external_id,
        last_seen=LAST_SEEN,
        creation_source=SIEMAgentCreationSource(
            vendor="splunk_enterprise",
            address=SourceAddress(
                instance=instance,
                scope="index=proxy",
                resource_id=external_id,
                query="index=proxy | stats count by agent",
            ),
            observations=AgentObservations(service_names=list(service_names)),
        ),
    )


@pytest.mark.unit_tests
def test_five_hundred_findings_produce_five_hundred_tasks_and_rescan_produces_none(
    resolver,
    db_session,
    tracked_tasks,
):
    """The scale case, and the re-scan that follows it.

    A Jamf fleet sweep returns hundreds of rows from one engine. Each is a distinct
    (software, device) finding and must end up on its own task; the run after it must
    land on exactly those tasks and mint nothing.
    """
    run = _run_id()
    records = [
        _endpoint_record(f"{run}-finding-{i}", device=f"C02XL4KHQ6N{i:03d}")
        for i in range(500)
    ]

    first_run = resolver.resolve_records(records).resolved
    tracked_tasks.extend(r.task_id for r in first_run)

    assert len(first_run) == 500
    assert len({r.task_id for r in first_run}) == 500
    assert {r.resolved_by for r in first_run} == {TaskResolutionMethod.CREATED}

    task_ids = [r.task_id for r in first_run]
    assert (
        db_session.query(DatabaseTask).filter(DatabaseTask.id.in_(task_ids)).count()
        == 500
    )

    second_run = resolver.resolve_records(records).resolved

    assert {r.resolved_by for r in second_run} == {TaskResolutionMethod.EXTERNAL_ID}
    assert {r.external_id: r.task_id for r in second_run} == {
        r.external_id: r.task_id for r in first_run
    }


@pytest.mark.unit_tests
def test_unknown_record_creates_a_task_carrying_its_sensor(
    resolver,
    db_session,
    tracked_tasks,
):
    """A record nothing knows yet mints a task that records what found it."""
    run = _run_id()
    record = _siem_record(f"{run}-splunk-1", name="Checkout Agent")

    [resolved] = resolver.resolve_records([record]).resolved
    tracked_tasks.append(resolved.task_id)

    assert resolved.resolved_by is TaskResolutionMethod.CREATED
    assert resolved.name == "Checkout Agent"

    db_task = db_session.query(DatabaseTask).filter_by(id=resolved.task_id).one()
    assert db_task.is_agentic is True
    assert db_task.is_autocreated is True
    assert db_task.task_metadata["creation_source"]["type"] == "SIEM"
    assert db_task.task_metadata["creation_source"]["vendor"] == "splunk_enterprise"
    # Nobody asked for this task, and an agent that is not sending traces has
    # nothing for a rule to evaluate.
    assert db_task.rule_links == []


@pytest.mark.unit_tests
def test_matching_external_id_routes_to_the_existing_task(
    resolver,
    tracked_tasks,
):
    """A second sighting of a known identity routes to its task, name changes included.

    Renaming on every scan would churn a field people sort and search on, so the task
    keeps the name it was minted with.
    """
    run = _run_id()
    external_id = f"{run}-openclaw"

    [first] = resolver.resolve_records([_endpoint_record(external_id, name="OpenClaw")]).resolved
    tracked_tasks.append(first.task_id)

    [second] = resolver.resolve_records(
        [_endpoint_record(external_id, name="OpenClaw (renamed upstream)")],
    ).resolved

    assert second.task_id == first.task_id
    assert second.resolved_by is TaskResolutionMethod.EXTERNAL_ID
    assert second.name == "OpenClaw"


@pytest.mark.unit_tests
def test_ha_install_reported_from_two_instances_shares_one_task(
    resolver,
    tracked_tasks,
):
    """Tasks are cluster-level: one external_id is one task, however many hosts run it.

    This is what keeps task volume tractable, and it is a property of the key rather
    than of the payload -- the address differs between these two records and must not
    enter the identity.
    """
    run = _run_id()
    external_id = f"{run}-regional-install"

    resolved = resolver.resolve_records(
        [
            _siem_record(external_id, instance="splunk-us-east-1"),
            _siem_record(external_id, instance="splunk-us-west-2"),
        ],
    ).resolved
    tracked_tasks.extend(r.task_id for r in resolved)

    assert len({r.task_id for r in resolved}) == 1
    assert [r.resolved_by for r in resolved] == [
        TaskResolutionMethod.CREATED,
        TaskResolutionMethod.EXTERNAL_ID,
    ]


@pytest.mark.unit_tests
def test_agent_instrumented_after_discovery_keeps_its_discovered_task(
    resolver,
    db_session,
    tracked_tasks,
):
    """The convergence the whole design turns on, in the order it usually happens.

    Someone instruments an agent a scan already found. Its traces arrive under a
    service name the sensor reported, and OTEL resolution finds the row discovery
    already wrote instead of auto-creating a second task.
    """
    run = _run_id()
    service_name = f"checkout-agent-{run}"

    [resolved] = resolver.resolve_records(
        [_siem_record(f"{run}-splunk-1", service_names=[service_name])],
    ).resolved
    tracked_tasks.append(resolved.task_id)
    assert resolved.resolved_by is TaskResolutionMethod.CREATED

    trace_task_id = TraceIngestionService(db_session)._resolve_task_id(
        explicit_task_id=None,
        service_name=service_name,
        resource_attributes={},
    )

    assert trace_task_id == resolved.task_id


@pytest.mark.unit_tests
def test_discovered_agent_already_sending_traces_joins_its_otel_task(
    resolver,
    db_session,
    tracked_tasks,
):
    """The same convergence from the other direction.

    An agent auto-created from its own traces is then found by a scan. It joins the
    task it already has, and its external_id is keyed to that task so the next scan
    resolves without consulting service names at all.
    """
    run = _run_id()
    service_name = f"already-traced-{run}"
    external_id = f"{run}-splunk-1"

    otel_task_id = TraceIngestionService(db_session)._resolve_task_id(
        explicit_task_id=None,
        service_name=service_name,
        resource_attributes={},
    )
    tracked_tasks.append(otel_task_id)

    [resolved] = resolver.resolve_records(
        [_siem_record(external_id, service_names=[service_name])],
    ).resolved

    assert resolved.task_id == otel_task_id
    assert resolved.resolved_by is TaskResolutionMethod.SERVICE_NAME
    assert (
        ServiceNameMappingRepository(db_session).get_task_id_by_service_name(
            external_id,
            MappingKeyKind.EXTERNAL_ID,
        )
        == otel_task_id
    )


@pytest.mark.unit_tests
def test_external_id_is_not_reported_as_a_service_name(
    resolver,
    db_session,
    tracked_tasks,
):
    """A task's service names are the names it emits telemetry under, and only those.

    `external_id` is keyed into the same table so the next scan can find the task, but
    it is a source's record ID. Reported as a service name, it tells the fetch job to
    look for traces under a name the agent never uses.
    """
    run = _run_id()
    service_name = f"checkout-agent-{run}"

    resolved = resolver.resolve_records(
        [
            _siem_record(f"{run}-splunk-1"),
            _siem_record(f"{run}-splunk-2", service_names=[service_name]),
        ],
    ).resolved
    tracked_tasks.extend(r.task_id for r in resolved)

    task_repo = resolver.task_repo
    assert not task_repo.get_task_by_id(resolved[0].task_id).service_names
    assert task_repo.get_task_by_id(resolved[1].task_id).service_names == [
        service_name,
    ]


@pytest.mark.unit_tests
def test_trace_named_like_an_external_id_does_not_join_its_task(
    resolver,
    db_session,
    tracked_tasks,
):
    """The same collision from the ingestion side.

    A source's record ID is not a claim on the telemetry namespace, so a trace whose
    `service.name` happens to match one is a different agent as far as ingestion can
    tell, and gets a task of its own.
    """
    run = _run_id()
    external_id = f"{run}-shared-string"

    [resolved] = resolver.resolve_records([_siem_record(external_id)]).resolved
    tracked_tasks.append(resolved.task_id)

    trace_task_id = TraceIngestionService(db_session)._resolve_task_id(
        explicit_task_id=None,
        service_name=external_id,
        resource_attributes={},
    )
    tracked_tasks.append(trace_task_id)

    assert trace_task_id != resolved.task_id

    # Both rows now exist under the one string, and each still routes its own kind.
    [rescanned] = resolver.resolve_records([_siem_record(external_id)]).resolved
    assert rescanned.task_id == resolved.task_id
    assert rescanned.resolved_by is TaskResolutionMethod.EXTERNAL_ID


@pytest.mark.unit_tests
def test_two_sources_reporting_one_agent_mint_two_tasks_without_a_shared_name(
    resolver,
    tracked_tasks,
):
    """v1's answer, recorded before D-03 assumes one.

    external_id is canonical and no identity resolution runs across sensors, so two
    sensors that share no key describe two agents as far as this step can tell.
    Corroboration is provenance's to express, by holding two evidence records against
    one task (D-09), not this resolver's to guess at.
    """
    run = _run_id()

    resolved = resolver.resolve_records(
        [
            _siem_record(f"{run}-splunk-1", name="Checkout Agent"),
            _endpoint_record(f"{run}-jamf-1", name="Checkout Agent"),
        ],
    ).resolved
    tracked_tasks.extend(r.task_id for r in resolved)

    assert len({r.task_id for r in resolved}) == 2


@pytest.mark.unit_tests
def test_two_sources_that_agree_on_a_service_name_share_one_task(
    resolver,
    tracked_tasks,
):
    """The one way two sensors do converge: they saw the same telemetry name."""
    run = _run_id()
    service_name = f"checkout-agent-{run}"

    resolved = resolver.resolve_records(
        [
            _siem_record(f"{run}-splunk-1", service_names=[service_name]),
            _endpoint_record(f"{run}-jamf-1", service_names=[service_name]),
        ],
    ).resolved
    tracked_tasks.extend(r.task_id for r in resolved)

    assert len({r.task_id for r in resolved}) == 1
    assert [r.resolved_by for r in resolved] == [
        TaskResolutionMethod.CREATED,
        TaskResolutionMethod.SERVICE_NAME,
    ]


@pytest.mark.unit_tests
def test_explicit_task_id_routes_to_that_task_and_keys_the_identity_to_it(
    resolver,
    db_session,
    tracked_tasks,
):
    """A caller that already knows the task is believed, and the key is written."""
    run = _run_id()
    external_id = f"{run}-splunk-1"

    [existing] = resolver.resolve_records([_siem_record(f"{run}-existing")]).resolved
    tracked_tasks.append(existing.task_id)

    [resolved] = resolver.resolve_records(
        [_endpoint_record(external_id, task_id=existing.task_id)],
    ).resolved

    assert resolved.task_id == existing.task_id
    assert resolved.resolved_by is TaskResolutionMethod.EXPLICIT_TASK_ID
    assert (
        ServiceNameMappingRepository(db_session).get_task_id_by_service_name(
            external_id,
            MappingKeyKind.EXTERNAL_ID,
        )
        == existing.task_id
    )


@pytest.mark.unit_tests
def test_explicit_task_id_cannot_move_an_identity_already_mapped(
    resolver,
    db_session,
    tracked_tasks,
):
    """A re-scan that names a different task resolves to the one that owns the identity.

    Mappings are immutable, so the claim cannot re-route a known agent. What matters is
    that the response agrees with the table: otherwise the agent's findings split
    across two tasks, and it flips between them depending on whether the caller sends
    `task_id`. The record's new service names follow the identity to its owner.
    """
    run = _run_id()
    external_id = f"{run}-openclaw"
    new_service_name = f"openclaw-{run}"

    [first] = resolver.resolve_records([_endpoint_record(external_id)]).resolved
    [other] = resolver.resolve_records([_siem_record(f"{run}-other")]).resolved
    tracked_tasks.extend([first.task_id, other.task_id])

    [rerouted] = resolver.resolve_records(
        [
            _endpoint_record(
                external_id,
                service_names=[new_service_name],
                task_id=other.task_id,
            ),
        ],
    ).resolved

    assert rerouted.task_id == first.task_id
    assert rerouted.resolved_by is TaskResolutionMethod.EXTERNAL_ID

    mapping_repo = ServiceNameMappingRepository(db_session)
    assert (
        mapping_repo.get_task_id_by_service_name(
            external_id,
            MappingKeyKind.EXTERNAL_ID,
        )
        == first.task_id
    )
    assert mapping_repo.get_task_id_by_service_name(new_service_name) == first.task_id

    [next_scan] = resolver.resolve_records([_endpoint_record(external_id)]).resolved
    assert next_scan.task_id == first.task_id


@pytest.mark.unit_tests
def test_explicit_task_id_that_does_not_exist_is_reported_not_minted(
    resolver,
    db_session,
):
    """Naming a task that is not there is a client error, not a silent mint."""
    run = _run_id()
    missing_task_id = str(uuid.uuid4())
    record = _endpoint_record(f"{run}-splunk-1", task_id=missing_task_id)

    outcome = resolver.resolve_records([record])

    assert outcome.resolved == []
    [failure] = outcome.failed
    assert failure.external_id == f"{run}-splunk-1"
    assert failure.task_id == missing_task_id
    assert failure.reason is DiscoveredRecordFailureReason.TASK_NOT_FOUND
    assert f"{run}-splunk-1" in failure.detail
    # Nothing was written for it: a later scan without the bad task_id starts fresh.
    assert (
        ServiceNameMappingRepository(db_session).get_task_id_by_service_name(
            f"{run}-splunk-1",
            MappingKeyKind.EXTERNAL_ID,
        )
        is None
    )


@pytest.mark.unit_tests
def test_one_bad_task_id_does_not_fail_the_rest_of_the_batch(
    resolver,
    tracked_tasks,
):
    """A scan of up to a thousand records is not held hostage by one bad row.

    Before, the bad record's 404 escaped mid-batch: the records ahead of it were
    committed, the ones behind it never ran, and re-submitting failed identically, so
    the scan job never got a 200 for that batch. Now every record lands in exactly one
    of `resolved` or `failed`, and a retry gets the same answer.
    """
    run = _run_id()
    missing_task_id = str(uuid.uuid4())
    records = [
        _siem_record(f"{run}-splunk-1"),
        _endpoint_record(f"{run}-bad", task_id=missing_task_id),
        _siem_record(f"{run}-splunk-3"),
    ]

    first = resolver.resolve_records(records)
    tracked_tasks.extend(r.task_id for r in first.resolved)

    assert [r.external_id for r in first.resolved] == [
        f"{run}-splunk-1",
        f"{run}-splunk-3",
    ]
    assert [f.external_id for f in first.failed] == [f"{run}-bad"]

    retry = resolver.resolve_records(records)

    assert [r.task_id for r in retry.resolved] == [r.task_id for r in first.resolved]
    assert {r.resolved_by for r in retry.resolved} == {
        TaskResolutionMethod.EXTERNAL_ID,
    }
    assert [f.external_id for f in retry.failed] == [f"{run}-bad"]


@pytest.mark.unit_tests
def test_task_deleted_mid_batch_fails_only_its_record(
    resolver,
    tracked_tasks,
):
    """The up-front check cannot see a task deleted after it ran.

    The mapping's foreign key refuses the write instead, and that record is reported
    the same way a bad `task_id` is, rather than failing the batch as a 500. SQLite
    does not enforce the key in these tests, so the refusal is raised directly.
    """
    run = _run_id()
    [target] = resolver.resolve_records([_siem_record(f"{run}-target")]).resolved
    tracked_tasks.append(target.task_id)

    original_create = resolver.mapping_repo.create_mapping

    def task_vanishes(key: str, task_id: str, key_kind: MappingKeyKind):
        if task_id == target.task_id:
            raise IntegrityError("INSERT", {}, Exception("foreign key violation"))
        return original_create(key, task_id, key_kind)

    resolver.mapping_repo.create_mapping = task_vanishes

    outcome = resolver.resolve_records(
        [
            _endpoint_record(f"{run}-late", task_id=target.task_id),
            _siem_record(f"{run}-unaffected"),
        ],
    )
    tracked_tasks.extend(r.task_id for r in outcome.resolved)

    assert [r.external_id for r in outcome.resolved] == [f"{run}-unaffected"]
    [failure] = outcome.failed
    assert failure.external_id == f"{run}-late"
    assert failure.task_id == target.task_id


@pytest.mark.unit_tests
def test_archived_task_still_wins_its_identity(resolver, db_session, tracked_tasks):
    """Archiving decides what is shown, not who an agent is.

    Minting a second task because the first was archived would break identity exactly
    where it matters most, so resolution routes to the archived task -- the same
    choice trace ingestion makes.
    """
    run = _run_id()
    external_id = f"{run}-openclaw"

    [first] = resolver.resolve_records([_endpoint_record(external_id)]).resolved
    tracked_tasks.append(first.task_id)
    db_session.query(DatabaseTask).filter_by(id=first.task_id).update(
        {"archived": True},
    )
    db_session.commit()

    [second] = resolver.resolve_records([_endpoint_record(external_id)]).resolved

    assert second.task_id == first.task_id
    assert second.resolved_by is TaskResolutionMethod.EXTERNAL_ID


@pytest.mark.unit_tests
def test_record_without_an_external_id_never_reaches_resolution():
    """The engine's backstop behind the connector output contract (D-13).

    A finding with no identity must fail, rather than route to the unmapped task and
    collapse silently together with every other such finding.
    """
    creation_source = _siem_record("placeholder").creation_source

    with pytest.raises(ValidationError):
        DiscoveredAgentRecord(
            name="Checkout Agent", creation_source=creation_source, last_seen=LAST_SEEN
        )

    with pytest.raises(ValidationError):
        DiscoveredAgentRecord(
            external_id="",
            name="Checkout Agent",
            last_seen=LAST_SEEN,
            creation_source=creation_source,
        )

    # A space is not an identity. `min_length` alone lets one through, and two agents
    # whose sources both reported one would key to the same mapping and collapse onto
    # a single task -- through the backstop meant to prevent exactly that.
    with pytest.raises(ValidationError):
        DiscoveredAgentRecord(
            external_id="   ",
            name="Checkout Agent",
            last_seen=LAST_SEEN,
            creation_source=creation_source,
        )


@pytest.mark.unit_tests
def test_record_with_a_blank_name_is_refused():
    """A whitespace-only name would mint a task that reads as nameless everywhere."""
    creation_source = _siem_record("placeholder").creation_source

    with pytest.raises(ValidationError):
        DiscoveredAgentRecord(
            external_id="splunk-1",
            name="  ",
            last_seen=LAST_SEEN,
            creation_source=creation_source,
        )


@pytest.mark.unit_tests
def test_names_keep_the_whitespace_the_source_reported(resolver, tracked_tasks):
    """Only blank values are refused; what a source calls an agent is left alone.

    Stripping would make the identity depend on this engine's idea of trailing space,
    which is the sort of quiet rewrite that turns one agent into two across a version
    bump.
    """
    run = _run_id()
    external_id = f" {run}-padded "

    [resolved] = resolver.resolve_records(
        [_endpoint_record(external_id, name=" Checkout Agent ")],
    ).resolved
    tracked_tasks.append(resolved.task_id)

    assert resolved.external_id == external_id
    assert resolved.name == " Checkout Agent "


@pytest.mark.unit_tests
def test_losing_a_concurrent_identity_claim_yields_to_the_winner(
    resolver,
    db_session,
    tracked_tasks,
):
    """The race rung 4 cannot read its way out of.

    Between reading the mappings and writing one, another request -- a second
    connector's batch, or trace ingestion auto-creating for a service name this scan
    is discovering -- can take `external_id` for a task of its own. `create_mapping`
    hands back the row that won, so the record resolves to the winner instead of
    reporting a task no key points at, and the task minted on the way is not left
    behind to be counted as an agent nobody will ever attribute a finding to.

    The winner is planted directly, which is what the losing request would have found
    had it committed a moment later.
    """
    run = _run_id()
    external_id = f"{run}-contested"

    [winner] = resolver.resolve_records([_siem_record(f"{run}-winner")]).resolved
    tracked_tasks.append(winner.task_id)

    # Claim the identity behind the resolver's back, after it has read the mappings.
    mapping_repo = ServiceNameMappingRepository(db_session)
    original_create = resolver.mapping_repo.create_mapping

    def claim_first(key: str, task_id: str, key_kind: MappingKeyKind):
        if key == external_id:
            mapping_repo.create_mapping(key, winner.task_id, key_kind)
        return original_create(key, task_id, key_kind)

    resolver.mapping_repo.create_mapping = claim_first

    [resolved] = resolver.resolve_records([_endpoint_record(external_id)]).resolved

    assert resolved.task_id == winner.task_id
    assert resolved.resolved_by is TaskResolutionMethod.EXTERNAL_ID
    # The task minted before the claim was lost is gone, not orphaned in the inventory.
    assert (
        db_session.query(DatabaseTask)
        .filter(DatabaseTask.name == external_id, DatabaseTask.id != winner.task_id)
        .count()
        == 0
    )


@pytest.mark.unit_tests
def test_a_source_a_scan_cannot_be_is_rejected():
    """OTEL and MANUAL are not things a scan finds.

    A record claiming either would mint a task whose provenance says nobody discovered
    it, so the input type does not admit them and the discriminator refuses the tag.
    """
    with pytest.raises(ValidationError):
        DiscoveredAgentRecord(
            external_id="checkout-agent",
            name="Checkout Agent",
            last_seen=LAST_SEEN,
            creation_source=OTELAgentCreationSource(),
        )
