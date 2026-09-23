"""The endpoints the ML Engine discovery jobs call (UP-4980 / D-08, UP-4981 / D-09).

Resolution itself is covered in tests/unit/services; what is tested here is the wire:
that a scan's batch round-trips through the API, that order is preserved so the caller
can line results up with the rows it sent, that a record with no identity is rejected
at the boundary, and that the fetch job can read back exactly the tasks one source
reported in a window, provenance intact.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    SIEMAgentCreationSource,
    SourceAddress,
)

from db_models import DatabaseTask, DatabaseTaskProvenanceSource
from db_models.telemetry_models import DatabaseServiceNameTaskMapping
from schemas.agent_discovery_schemas import (
    DiscoveredRecordFailureReason,
    TaskResolutionMethod,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)

# Every record carries the time its source last saw the agent. Resolution does not read
# it, so one fixed instant keeps it out of the way of what these tests are about.
LAST_SEEN = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _record(
    external_id: str,
    name: str,
    service_names=(),
    task_id: str | None = None,
) -> DiscoveredAgentRecord:
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=name,
        last_seen=LAST_SEEN,
        task_id=task_id,
        creation_source=SIEMAgentCreationSource(
            vendor="splunk_enterprise",
            address=SourceAddress(
                instance="splunk-prod",
                scope="index=proxy",
                resource_id=external_id,
            ),
            observations=AgentObservations(service_names=list(service_names)),
        ),
    )


def _cleanup(task_ids: list[str]) -> None:
    db_session = override_get_db_session()
    try:
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
    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_resolve_returns_a_task_per_record_in_request_order(
    client: GenaiEngineTestClientBase,
):
    run = uuid.uuid4().hex[:8]
    records = [_record(f"{run}-splunk-{i}", name=f"Agent {i}") for i in range(3)]

    status_code, response = client.resolve_discovered_agents(records)
    assert status_code == 200

    task_ids = [r.task_id for r in response.resolved]
    try:
        assert [r.external_id for r in response.resolved] == [
            r.external_id for r in records
        ]
        assert len(set(task_ids)) == 3
        assert response.failed == []
        assert all(
            r.resolved_by is TaskResolutionMethod.CREATED for r in response.resolved
        )

        # Resubmitting the same batch is the re-scan case, over the wire.
        status_code, second = client.resolve_discovered_agents(records)
        assert status_code == 200
        assert [r.task_id for r in second.resolved] == task_ids
        assert all(
            r.resolved_by is TaskResolutionMethod.EXTERNAL_ID for r in second.resolved
        )
    finally:
        _cleanup(task_ids)


@pytest.mark.unit_tests
def test_bad_task_id_is_reported_while_the_rest_of_the_batch_resolves(
    client: GenaiEngineTestClientBase,
):
    """A 200 that says which records landed, rather than a 404 that says none did."""
    run = uuid.uuid4().hex[:8]
    missing_task_id = str(uuid.uuid4())
    records = [
        _record(f"{run}-splunk-1", name="Agent 1"),
        _record(f"{run}-bad", name="Agent 2", task_id=missing_task_id),
        _record(f"{run}-splunk-3", name="Agent 3"),
    ]

    status_code, response = client.resolve_discovered_agents(records)
    assert status_code == 200

    try:
        assert [r.external_id for r in response.resolved] == [
            f"{run}-splunk-1",
            f"{run}-splunk-3",
        ]
        [failure] = response.failed
        assert failure.external_id == f"{run}-bad"
        assert failure.task_id == missing_task_id
        assert failure.reason is DiscoveredRecordFailureReason.TASK_NOT_FOUND
    finally:
        _cleanup([r.task_id for r in response.resolved])


@pytest.mark.unit_tests
def test_resolved_tasks_show_up_as_agent_tasks(
    client: GenaiEngineTestClientBase,
):
    """A minted task is an agent like any other, and reads back with its sensor."""
    run = uuid.uuid4().hex[:8]
    status_code, response = client.resolve_discovered_agents(
        [_record(f"{run}-splunk-1", name=f"Checkout Agent {run}")],
    )
    assert status_code == 200
    task_id = response.resolved[0].task_id

    try:
        status_code, agent_tasks = client.get_agent_tasks()
        assert status_code == 200

        minted = [task for task in agent_tasks if task.id == task_id]
        assert len(minted) == 1
        assert minted[0].creation_source.root.type == "SIEM"
        assert minted[0].creation_source.root.vendor == "splunk_enterprise"
        # The record's external_id is keyed to this task, but it is not a name the
        # agent emits telemetry under.
        assert minted[0].creation_source.root.observations.service_names == []
    finally:
        _cleanup([task_id])


@pytest.mark.unit_tests
def test_record_without_an_external_id_is_rejected_at_the_boundary(
    client: GenaiEngineTestClientBase,
):
    """D-13 rejects it upstream; the engine refuses it too rather than guessing.

    400 rather than 422: `GenaiEngineRoute` maps every request validation failure to
    400, so that is what a malformed body looks like on this API.
    """
    payload = _record("placeholder", name="Checkout Agent").model_dump(mode="json")
    payload.pop("external_id")

    resp = client.base_client.post(
        "api/v2/agent-tasks/resolve",
        json={"source_id": str(uuid.uuid4()), "records": [payload]},
        headers=client.authorized_user_api_key_headers,
    )

    assert resp.status_code == 400


@pytest.mark.unit_tests
def test_empty_batch_is_rejected(client: GenaiEngineTestClientBase):
    resp = client.base_client.post(
        "api/v2/agent-tasks/resolve",
        json={"source_id": str(uuid.uuid4()), "records": []},
        headers=client.authorized_user_api_key_headers,
    )

    assert resp.status_code == 400


@pytest.mark.unit_tests
def test_batch_without_a_source_is_rejected(client: GenaiEngineTestClientBase):
    """A record resolved without a source could never be fetched back for it."""
    payload = _record("placeholder", name="Checkout Agent").model_dump(mode="json")

    resp = client.base_client.post(
        "api/v2/agent-tasks/resolve",
        json={"records": [payload]},
        headers=client.authorized_user_api_key_headers,
    )

    assert resp.status_code == 400


@pytest.mark.unit_tests
def test_agent_tasks_scoped_to_a_source_return_only_its_tasks(
    client: GenaiEngineTestClientBase,
):
    """What the fetch job reads after a scan: that source's tasks, with provenance."""
    run = uuid.uuid4().hex[:8]
    ours, theirs = uuid.uuid4(), uuid.uuid4()

    _, our_batch = client.resolve_discovered_agents(
        [_record(f"{run}-ours-{i}", name=f"Ours {i}") for i in range(2)],
        source_id=ours,
    )
    _, their_batch = client.resolve_discovered_agents(
        [_record(f"{run}-theirs", name="Theirs")],
        source_id=theirs,
    )
    our_task_ids = {r.task_id for r in our_batch.resolved}
    task_ids = [*our_task_ids, *(r.task_id for r in their_batch.resolved)]

    try:
        status_code, agent_tasks = client.get_agent_tasks(discovery_source_id=ours)
        assert status_code == 200

        assert {task.id for task in agent_tasks} == our_task_ids
        for task in agent_tasks:
            [entry] = task.provenance.sources
            assert entry.source_id == ours
            assert entry.vendor == "splunk_enterprise"
            assert entry.address.instance == "splunk-prod"
    finally:
        _cleanup(task_ids)


@pytest.mark.unit_tests
def test_agent_tasks_since_include_rescanned_tasks_and_exclude_stale_ones(
    client: GenaiEngineTestClientBase,
):
    """The window is on when a scan last reported the task, not when it was minted.

    A re-scan resolves to tasks that already exist; if the window were on creation, the
    fetch job would hear about an agent only on the day it was first found.
    """
    run = uuid.uuid4().hex[:8]
    source_id = uuid.uuid4()
    rescanned = _record(f"{run}-rescanned", name="Rescanned")
    stale = _record(f"{run}-stale", name="Stale")

    _, first = client.resolve_discovered_agents([rescanned, stale], source_id=source_id)
    task_ids = [r.task_id for r in first.resolved]
    rescanned_task_id, stale_task_id = task_ids

    try:
        # Both were first reported a day ago...
        a_day_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        db_session = override_get_db_session()
        try:
            db_session.query(DatabaseTaskProvenanceSource).filter(
                DatabaseTaskProvenanceSource.task_id.in_(task_ids),
            ).update(
                {"first_reported_at": a_day_ago, "last_reported_at": a_day_ago},
                synchronize_session=False,
            )
            db_session.commit()
        finally:
            db_session.close()

        # ...and only one of them turned up again in this scan.
        window_start = datetime.now(timezone.utc) - timedelta(minutes=5)
        _, second = client.resolve_discovered_agents([rescanned], source_id=source_id)
        assert second.resolved[0].task_id == rescanned_task_id

        status_code, agent_tasks = client.get_agent_tasks(
            discovery_source_id=source_id,
            reported_since=window_start,
        )
        assert status_code == 200
        assert [task.id for task in agent_tasks] == [rescanned_task_id]

        # Widening the window brings the stale one back.
        _, everything = client.get_agent_tasks(
            discovery_source_id=source_id,
            reported_since=window_start - timedelta(days=2),
        )
        assert {task.id for task in everything} == {rescanned_task_id, stale_task_id}
    finally:
        _cleanup(task_ids)


@pytest.mark.unit_tests
def test_agent_tasks_for_a_source_with_no_reports_is_empty(
    client: GenaiEngineTestClientBase,
):
    """An empty answer, not every task: a filter matching nothing must not fall away."""
    status_code, agent_tasks = client.get_agent_tasks(discovery_source_id=uuid.uuid4())

    assert status_code == 200
    assert agent_tasks == []
