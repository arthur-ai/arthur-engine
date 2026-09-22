"""The endpoint the ML Engine scan job calls (UP-4980 / D-08).

Resolution itself is covered in tests/unit/services; what is tested here is the wire:
that a scan's batch round-trips through the API, that order is preserved so the caller
can line results up with the rows it sent, and that a record with no identity is
rejected at the boundary.
"""

import uuid
from datetime import datetime, timezone

import pytest
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    SIEMAgentCreationSource,
    SourceAddress,
)

from db_models import DatabaseTask
from db_models.telemetry_models import DatabaseServiceNameTaskMapping
from schemas.agent_discovery_schemas import TaskResolutionMethod
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)

# Every record carries the time its source last saw the agent. Resolution does not read
# it, so one fixed instant keeps it out of the way of what these tests are about.
LAST_SEEN = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _record(external_id: str, name: str, service_names=()) -> DiscoveredAgentRecord:
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=name,
        last_seen=LAST_SEEN,
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
        json={"records": [payload]},
        headers=client.authorized_user_api_key_headers,
    )

    assert resp.status_code == 400


@pytest.mark.unit_tests
def test_empty_batch_is_rejected(client: GenaiEngineTestClientBase):
    resp = client.base_client.post(
        "api/v2/agent-tasks/resolve",
        json={"records": []},
        headers=client.authorized_user_api_key_headers,
    )

    assert resp.status_code == 400
