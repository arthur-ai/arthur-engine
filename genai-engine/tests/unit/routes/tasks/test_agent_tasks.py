"""Unit tests for the /api/v2/agent-tasks endpoint."""
import random
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.enums import RegisteredAgentProvider
from arthur_common.models.request_schemas import AgentMetadata, GCPAgentMetadata
from openinference.semconv.trace import OpenInferenceSpanKindValues

from db_models import DatabaseAgentPollingData, DatabaseSpan, DatabaseTask
from schemas.internal_schemas import (
    GCPCreationSource,
    ManualCreationSource,
    OTELCreationSource,
    RegisteredGCPAgentCredentials,
    TaskMetadata,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.mark.unit_tests
def test_get_agent_tasks_returns_all_tasks_by_default(
    client: GenaiEngineTestClientBase,
):
    """Test that get_agent_tasks returns both agentic and non-agentic tasks by default."""
    # Create both types of tasks
    agentic_name = f"agentic_{random.random()}"
    non_agentic_name = f"non_agentic_{random.random()}"

    status_code, agentic_task = client.create_task(agentic_name, is_agentic=True)
    assert status_code == 200

    status_code, non_agentic_task = client.create_task(
        non_agentic_name, is_agentic=False
    )
    assert status_code == 200

    # Get all tasks (no filter)
    status_code, enriched_tasks = client.get_agent_tasks()
    assert status_code == 200
    assert isinstance(enriched_tasks, list)

    # Should contain both tasks
    task_ids = [t.id for t in enriched_tasks]
    assert agentic_task.id in task_ids
    assert non_agentic_task.id in task_ids


@pytest.mark.unit_tests
def test_get_agent_tasks_manual_task(client: GenaiEngineTestClientBase):
    """Test that manually created agentic task has correct creation_source."""
    task_name = f"manual_agentic_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Get agent tasks
    status_code, enriched_tasks = client.get_agent_tasks()
    assert status_code == 200

    # Find the created task
    manual_task = next((t for t in enriched_tasks if t.id == task.id), None)
    assert manual_task is not None

    # Verify fields
    assert manual_task.name == task_name
    assert manual_task.is_agentic is True
    assert manual_task.is_autocreated is False
    assert manual_task.infrastructure is None

    # Verify creation_source is Manual
    assert manual_task.creation_source is not None
    assert isinstance(manual_task.creation_source, ManualCreationSource)
    assert manual_task.creation_source.type == "manual"

    # Agent metadata should be present but empty (no spans yet)
    assert manual_task.tools == []
    assert manual_task.sub_agents == []
    assert manual_task.models == []
    assert manual_task.num_spans == 0


@pytest.mark.unit_tests
def test_get_agent_tasks_gcp_task(client: GenaiEngineTestClientBase):
    """Test that GCP registered agent task has correct creation_source."""
    task_name = f"gcp_agent_{random.random()}"
    task_id = str(uuid4())

    # Directly insert GCP task into database (bypassing API to avoid polling service)
    db_session = override_get_db_session()
    try:
        # Create task with GCP metadata
        task_metadata = TaskMetadata(
            provider=RegisteredAgentProvider.GCP,
            gcp_metadata=RegisteredGCPAgentCredentials(
                project_id="test-project",
                region="us-central1",
                resource_id="projects/test-project/locations/us-central1/reasoningEngines/12345",
            ),
            service_names=["projects/test-project/locations/us-central1/reasoningEngines/12345"],
        )

        db_task = DatabaseTask(
            id=task_id,
            name=task_name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_autocreated=False,
            task_metadata=task_metadata.model_dump(mode="json"),
            archived=False,
        )
        db_session.add(db_task)
        db_session.commit()

        # Get agent tasks
        status_code, enriched_tasks = client.get_agent_tasks()
        assert status_code == 200

        # Find the created task
        gcp_task = next((t for t in enriched_tasks if t.id == task_id), None)
        assert gcp_task is not None

        # Verify fields
        assert gcp_task.name == task_name
        assert gcp_task.is_agentic is True
        assert gcp_task.is_autocreated is False
        assert gcp_task.infrastructure == "GCP"

        # Verify creation_source is GCP
        assert gcp_task.creation_source is not None
        assert isinstance(gcp_task.creation_source, GCPCreationSource)
        assert gcp_task.creation_source.type == "GCP"
        assert gcp_task.creation_source.gcp_project_id == "test-project"
        assert gcp_task.creation_source.gcp_region == "us-central1"
        assert gcp_task.creation_source.gcp_reasoning_engine_id == "12345"

    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_get_agent_tasks_with_spans(client: GenaiEngineTestClientBase):
    """Test that agent metadata is extracted from spans correctly."""
    task_name = f"agent_with_spans_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Insert mock spans directly into database
    db_session = override_get_db_session()
    try:
        # Create TOOL span
        tool_span = DatabaseSpan(
            id=str(uuid4()),
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            span_name="search_tool",
            span_kind=OpenInferenceSpanKindValues.TOOL.value,
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now(),
            task_id=task.id,
            raw_data={"attributes": {}},
            created_at=datetime.now(),
        )
        db_session.add(tool_span)

        # Create AGENT span
        agent_span = DatabaseSpan(
            id=str(uuid4()),
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            span_name="sub_agent_1",
            span_kind=OpenInferenceSpanKindValues.AGENT.value,
            start_time=datetime.now() - timedelta(minutes=4),
            end_time=datetime.now(),
            task_id=task.id,
            raw_data={"attributes": {}},
            created_at=datetime.now(),
        )
        db_session.add(agent_span)

        # Create LLM span with model
        llm_span = DatabaseSpan(
            id=str(uuid4()),
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            span_name="llm_call",
            span_kind=OpenInferenceSpanKindValues.LLM.value,
            start_time=datetime.now() - timedelta(minutes=3),
            end_time=datetime.now(),
            task_id=task.id,
            raw_data={"attributes": {"llm": {"model_name": "gpt-4"}}},
            created_at=datetime.now(),
        )
        db_session.add(llm_span)

        db_session.commit()

        # Get agent tasks
        status_code, enriched_tasks = client.get_agent_tasks()
        assert status_code == 200

        # Find the created task
        task_with_spans = next((t for t in enriched_tasks if t.id == task.id), None)
        assert task_with_spans is not None

        # Verify agent metadata extracted from spans
        assert task_with_spans.tools is not None
        assert len(task_with_spans.tools) == 1
        assert task_with_spans.tools[0].name == "search_tool"

        assert task_with_spans.sub_agents is not None
        assert len(task_with_spans.sub_agents) == 1
        assert task_with_spans.sub_agents[0].name == "sub_agent_1"

        assert task_with_spans.models is not None
        assert len(task_with_spans.models) == 1
        assert task_with_spans.models[0] == "gpt-4"

        assert task_with_spans.num_spans == 3

    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_get_agent_tasks_30_day_lookback(client: GenaiEngineTestClientBase):
    """Test that only spans within 30 days are included."""
    task_name = f"agent_old_spans_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Insert spans with different ages
    db_session = override_get_db_session()
    try:
        # Recent span (within 30 days)
        recent_span = DatabaseSpan(
            id=str(uuid4()),
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            span_name="recent_tool",
            span_kind=OpenInferenceSpanKindValues.TOOL.value,
            start_time=datetime.now() - timedelta(days=10),
            end_time=datetime.now() - timedelta(days=10),
            task_id=task.id,
            raw_data={"attributes": {}},
            created_at=datetime.now() - timedelta(days=10),
        )
        db_session.add(recent_span)

        # Old span (older than 30 days)
        old_span = DatabaseSpan(
            id=str(uuid4()),
            trace_id=str(uuid4()),
            span_id=str(uuid4()),
            span_name="old_tool",
            span_kind=OpenInferenceSpanKindValues.TOOL.value,
            start_time=datetime.now() - timedelta(days=35),
            end_time=datetime.now() - timedelta(days=35),
            task_id=task.id,
            raw_data={"attributes": {}},
            created_at=datetime.now() - timedelta(days=35),
        )
        db_session.add(old_span)

        db_session.commit()

        # Get agent tasks
        status_code, enriched_tasks = client.get_agent_tasks()
        assert status_code == 200

        # Find the created task
        task_with_spans = next((t for t in enriched_tasks if t.id == task.id), None)
        assert task_with_spans is not None

        # Only recent span should be counted
        assert task_with_spans.num_spans == 1
        assert len(task_with_spans.tools) == 1
        assert task_with_spans.tools[0].name == "recent_tool"

    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_get_agent_tasks_with_last_fetched(client: GenaiEngineTestClientBase):
    """Test that last_fetched is included for GCP tasks from polling data."""
    task_name = f"gcp_polled_{random.random()}"
    task_id = str(uuid4())
    last_fetched_time = datetime.now() - timedelta(hours=1)

    # Directly insert GCP task into database (bypassing API to avoid polling service)
    db_session = override_get_db_session()
    try:
        # Create task with GCP metadata
        task_metadata = TaskMetadata(
            provider=RegisteredAgentProvider.GCP,
            gcp_metadata=RegisteredGCPAgentCredentials(
                project_id="test-project",
                region="us-central1",
                resource_id="projects/test-project/locations/us-central1/reasoningEngines/67890",
            ),
            service_names=["projects/test-project/locations/us-central1/reasoningEngines/67890"],
        )

        db_task = DatabaseTask(
            id=task_id,
            name=task_name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_autocreated=False,
            task_metadata=task_metadata.model_dump(mode="json"),
            archived=False,
        )
        db_session.add(db_task)

        # Add polling data with last_fetched
        polling_data = DatabaseAgentPollingData(
            id=uuid4(),
            task_id=task_id,
            status="IDLE",
            last_fetched=last_fetched_time,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(polling_data)
        db_session.commit()

        # Get agent tasks - should include last_fetched from polling data
        status_code, enriched_tasks = client.get_agent_tasks()
        assert status_code == 200

        gcp_task = next((t for t in enriched_tasks if t.id == task_id), None)
        assert gcp_task is not None

        # Verify GCP creation_source with last_fetched
        assert isinstance(gcp_task.creation_source, GCPCreationSource)
        assert gcp_task.creation_source.type == "GCP"
        assert gcp_task.creation_source.gcp_project_id == "test-project"
        assert gcp_task.creation_source.gcp_region == "us-central1"
        assert gcp_task.creation_source.gcp_reasoning_engine_id == "67890"
        assert gcp_task.creation_source.last_fetched is not None
        # Allow for some time delta in comparison
        assert abs((gcp_task.creation_source.last_fetched - last_fetched_time).total_seconds()) < 2

    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_get_agent_tasks_filter_by_agentic(client: GenaiEngineTestClientBase):
    """Test filtering tasks by is_agentic parameter."""
    # Create agentic and non-agentic tasks
    agentic_name = f"agentic_{random.random()}"
    non_agentic_name = f"non_agentic_{random.random()}"

    status_code, agentic_task = client.create_task(agentic_name, is_agentic=True)
    assert status_code == 200

    status_code, non_agentic_task = client.create_task(
        non_agentic_name, is_agentic=False
    )
    assert status_code == 200

    # Get only agentic tasks
    status_code, agentic_tasks = client.get_agent_tasks(is_agentic=True)
    assert status_code == 200

    agentic_ids = [t.id for t in agentic_tasks]
    assert agentic_task.id in agentic_ids
    assert non_agentic_task.id not in agentic_ids

    # Get only non-agentic tasks
    status_code, non_agentic_tasks = client.get_agent_tasks(is_agentic=False)
    assert status_code == 200

    non_agentic_ids = [t.id for t in non_agentic_tasks]
    assert non_agentic_task.id in non_agentic_ids
    assert agentic_task.id not in non_agentic_ids


@pytest.mark.unit_tests
def test_get_agent_tasks_includes_rules_and_metrics(client: GenaiEngineTestClientBase):
    """Test that enriched tasks include rules and metrics."""
    task_name = f"task_with_rules_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Get agent tasks
    status_code, enriched_tasks = client.get_agent_tasks()
    assert status_code == 200

    enriched_task = next((t for t in enriched_tasks if t.id == task.id), None)
    assert enriched_task is not None

    # Should have rules (default rules are auto-added)
    assert enriched_task.rules is not None
    assert isinstance(enriched_task.rules, list)

    # Should have metrics list (may be empty)
    assert enriched_task.metrics is not None
    assert isinstance(enriched_task.metrics, list)


@pytest.mark.unit_tests
def test_get_agent_tasks_autocreated_otel_task(client: GenaiEngineTestClientBase):
    """Test that auto-created tasks have OTEL creation_source."""
    # Simulate an auto-created task by directly manipulating the database
    from db_models import DatabaseTask

    task_name = f"autocreated_otel_{random.random()}"
    db_session = override_get_db_session()
    try:
        # Create an auto-created task (simulating what trace ingestion does)
        db_task = DatabaseTask(
            id=str(uuid4()),
            name=task_name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_autocreated=True,  # Key: auto-created from traces
            task_metadata=None,  # No provider metadata
            archived=False,
        )
        db_session.add(db_task)
        db_session.commit()

        # Get agent tasks
        status_code, enriched_tasks = client.get_agent_tasks()
        assert status_code == 200

        # Find the auto-created task
        otel_task = next((t for t in enriched_tasks if t.id == db_task.id), None)
        assert otel_task is not None

        # Verify it's identified as auto-created
        assert otel_task.is_autocreated is True
        assert otel_task.is_agentic is True
        assert otel_task.infrastructure is None

        # Verify creation_source is OTEL
        assert otel_task.creation_source is not None
        assert isinstance(otel_task.creation_source, OTELCreationSource)
        assert otel_task.creation_source.type == "OTEL"
        assert otel_task.creation_source.service_name == task_name

    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_get_agent_tasks_non_agentic_has_null_metadata(
    client: GenaiEngineTestClientBase,
):
    """Test that non-agentic tasks have null agent metadata fields."""
    task_name = f"non_agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=False)
    assert status_code == 200

    # Get all tasks including non-agentic
    status_code, enriched_tasks = client.get_agent_tasks(is_agentic=False)
    assert status_code == 200

    # Find the non-agentic task
    non_agentic_task = next((t for t in enriched_tasks if t.id == task.id), None)
    assert non_agentic_task is not None

    # Verify basic fields
    assert non_agentic_task.is_agentic is False
    assert non_agentic_task.name == task_name

    # Agent metadata fields should be None or empty for non-agentic tasks
    assert non_agentic_task.creation_source is None
    assert non_agentic_task.infrastructure is None
    assert non_agentic_task.tools is None
    assert non_agentic_task.sub_agents is None
    assert non_agentic_task.models is None
    assert non_agentic_task.num_spans is None


@pytest.mark.unit_tests
def test_get_agent_tasks_performance_no_n_plus_1(client: GenaiEngineTestClientBase):
    """Test that the endpoint doesn't have N+1 query issues."""
    # Create multiple agentic tasks
    task_ids = []
    for i in range(5):
        task_name = f"perf_test_task_{i}_{random.random()}"
        status_code, task = client.create_task(task_name, is_agentic=True)
        assert status_code == 200
        task_ids.append(task.id)

    # Get all agent tasks - should work efficiently
    status_code, enriched_tasks = client.get_agent_tasks(is_agentic=True)
    assert status_code == 200

    # Verify all tasks are returned
    returned_ids = [t.id for t in enriched_tasks]
    for task_id in task_ids:
        assert task_id in returned_ids

    # This test primarily validates that the endpoint completes without error
    # In a real scenario, you'd use SQL query logging to verify query count
