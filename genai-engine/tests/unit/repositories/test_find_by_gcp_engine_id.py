"""`TaskRepository.find_by_gcp_engine_id` across both shapes a Vertex task's row holds.

Run against the unit-test database itself rather than a mock, so the JSON path the
query takes is the one exercised.
"""

import uuid
from datetime import datetime, timedelta

import pytest
from arthur_common.models.agent_governance_schemas import (
    AgentCreationSource,
    AgentObservations,
    CloudAgentCreationSource,
    GCPAgentCreationSource,
    SourceAddress,
    TaskMetadata,
)

from db_models import DatabaseTask
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from tests.clients.base_test_client import override_get_db_session


def _metadata(creation_source) -> dict:
    return TaskMetadata(
        creation_source=AgentCreationSource(root=creation_source),
    ).model_dump(mode="json")


def _connector_source(engine_id: str, vendor: str = "gcp_vertex"):
    return CloudAgentCreationSource(
        vendor=vendor,
        address=SourceAddress(
            instance="proj-a",
            scope="us-central1",
            resource_id=engine_id,
        ),
        observations=AgentObservations(
            service_names=[
                f"projects/123/locations/us-central1/reasoningEngines/{engine_id}",
            ],
        ),
    )


def _legacy_source(engine_id: str):
    return GCPAgentCreationSource(
        gcp_project_id="proj-a",
        gcp_region="us-central1",
        gcp_reasoning_engine_id=engine_id,
    )


@pytest.fixture
def env(client):
    db_session = override_get_db_session()
    repo = TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        get_application_config(session=db_session),
    )
    created: list[str] = []

    def add_task(task_metadata: dict, created_at: datetime | None = None) -> str:
        sc, task = client.create_task(name=f"vertex-{uuid.uuid4()}")
        assert sc == 200
        values: dict = {"task_metadata": task_metadata}
        if created_at is not None:
            values["created_at"] = created_at
        db_session.query(DatabaseTask).filter(DatabaseTask.id == task.id).update(
            values,
        )
        db_session.commit()
        created.append(task.id)
        return task.id

    yield repo, add_task
    for task_id in created:
        client.delete_task(task_id)


@pytest.mark.unit_tests
def test_finds_a_connector_created_task_by_address_resource_id(env):
    repo, add_task = env
    engine_id = str(uuid.uuid4())
    task_id = add_task(_metadata(_connector_source(engine_id)))

    found = repo.find_by_gcp_engine_id(engine_id)

    assert found is not None
    assert found.id == task_id


@pytest.mark.unit_tests
def test_finds_a_legacy_task_by_its_flat_field(env):
    repo, add_task = env
    engine_id = str(uuid.uuid4())
    task_id = add_task(_metadata(_legacy_source(engine_id)))

    found = repo.find_by_gcp_engine_id(engine_id)

    assert found is not None
    assert found.id == task_id


@pytest.mark.unit_tests
def test_finds_a_legacy_row_stored_before_address_existed(env):
    """Rows the legacy poller wrote before the model serialized `address` carry the
    flat field alone, and are the bulk of what deployed engines hold."""
    repo, add_task = env
    engine_id = str(uuid.uuid4())
    task_id = add_task(
        {
            "creation_source": {
                "type": "GCP",
                "gcp_project_id": "proj-a",
                "gcp_region": "us-central1",
                "gcp_reasoning_engine_id": engine_id,
            },
        },
    )

    found = repo.find_by_gcp_engine_id(engine_id)

    assert found is not None
    assert found.id == task_id


@pytest.mark.unit_tests
def test_ignores_another_vendors_identical_resource_id(env):
    repo, add_task = env
    engine_id = str(uuid.uuid4())
    add_task(_metadata(_connector_source(engine_id, vendor="aws_bedrock")))

    assert repo.find_by_gcp_engine_id(engine_id) is None


@pytest.mark.unit_tests
def test_returns_none_for_an_unknown_engine(env):
    repo, add_task = env
    add_task(_metadata(_connector_source(str(uuid.uuid4()))))

    assert repo.find_by_gcp_engine_id(str(uuid.uuid4())) is None


@pytest.mark.unit_tests
def test_prefers_the_older_task_when_both_shapes_name_one_engine(env):
    """While both discovery paths run, one engine can briefly have a legacy task and
    a connector task; traces keep going to the one that already has them."""
    repo, add_task = env
    engine_id = str(uuid.uuid4())
    now = datetime.now()
    legacy_id = add_task(
        _metadata(_legacy_source(engine_id)),
        created_at=now - timedelta(days=10),
    )
    add_task(_metadata(_connector_source(engine_id)), created_at=now)

    found = repo.find_by_gcp_engine_id(engine_id)

    assert found is not None
    assert found.id == legacy_id
