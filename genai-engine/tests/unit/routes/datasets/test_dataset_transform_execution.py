"""Tests for dataset transform execution endpoint."""

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from db_models import DatabaseSpan, DatabaseTask, DatabaseTraceMetadata
from schemas.internal_schemas import Span as InternalSpan
from services.trace.span_normalization_service import SpanNormalizationService
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.fixture(scope="function")
def setup_test_data():
    """Setup test data including task, trace, and spans."""
    db_session: Session = override_get_db_session()
    span_normalizer = SpanNormalizationService()

    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    # Create task
    task = DatabaseTask(
        id=task_id,
        name="Test Task for Transform Execution",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(task)
    db_session.commit()

    # Create spans with nested attributes
    base_time = datetime.now()

    # Span 1: RAG retrieval span with sqlQuery
    span1_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "rag-retrieval-savedQueries",
            "spanId": f"span1_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "RETRIEVER",
                "input.value.sqlQuery": "SELECT * FROM users WHERE id = 1",
                "input.value.context": "User query context",
                "output.value.results": [{"id": 1, "name": "John"}],
            },
        },
    )
    span1_raw_data["arthur_span_version"] = "arthur_span_v1"

    span1 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span1_raw_data["spanId"],
        task_id=task_id,
        parent_span_id=None,
        span_kind="RETRIEVER",
        start_time=base_time,
        end_time=base_time,
        session_id=None,
        user_id=None,
        raw_data=span1_raw_data,
        created_at=base_time,
        updated_at=base_time,
    )

    # Span 2: LLM span with token costs
    span2_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "llm_call",
            "spanId": f"span2_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.token_cost": 0.05,
                "llm.token_count.prompt": 100,
                "llm.token_count.completion": 50,
            },
        },
    )
    span2_raw_data["arthur_span_version"] = "arthur_span_v1"

    span2 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span2_raw_data["spanId"],
        task_id=task_id,
        parent_span_id=None,
        span_kind="LLM",
        start_time=base_time,
        end_time=base_time,
        session_id=None,
        user_id=None,
        raw_data=span2_raw_data,
        created_at=base_time,
        updated_at=base_time,
    )

    # Span 3: Span with nested child
    span3_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "agent_span",
            "spanId": f"span3_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "AGENT",
                "agent.name": "test_agent",
            },
        },
    )
    span3_raw_data["arthur_span_version"] = "arthur_span_v1"

    span3 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span3_raw_data["spanId"],
        task_id=task_id,
        parent_span_id=span1_raw_data["spanId"],  # Child of span1
        span_kind="AGENT",
        start_time=base_time,
        end_time=base_time,
        session_id=None,
        user_id=None,
        raw_data=span3_raw_data,
        created_at=base_time,
        updated_at=base_time,
    )

    # Create database spans
    spans = [span1, span2, span3]
    database_spans = []
    for span in spans:
        db_span = DatabaseSpan(
            id=span.id,
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            span_name=span.raw_data.get("name"),
            span_kind=span.span_kind,
            start_time=span.start_time,
            end_time=span.end_time,
            task_id=span.task_id,
            session_id=span.session_id,
            user_id=span.user_id,
            status_code="Ok",
            raw_data=span.raw_data,
            created_at=span.created_at,
            updated_at=span.updated_at,
        )
        database_spans.append(db_span)

    db_session.add_all(database_spans)
    db_session.commit()

    # Create trace metadata
    trace_metadata = DatabaseTraceMetadata(
        task_id=task_id,
        trace_id=trace_id,
        session_id=None,
        user_id=None,
        span_count=len(spans),
        start_time=base_time,
        end_time=base_time,
        created_at=base_time,
        updated_at=base_time,
        input_content="test input",
        output_content="test output",
    )
    db_session.add(trace_metadata)
    db_session.commit()

    yield {
        "task_id": task_id,
        "trace_id": trace_id,
        "spans": spans,
        "db_session": db_session,
    }

    # Cleanup
    db_session.query(DatabaseSpan).filter(DatabaseSpan.trace_id == trace_id).delete()
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id == trace_id,
    ).delete()
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
    db_session.commit()


@pytest.mark.unit_tests
def test_execute_transform_success(
    client: GenaiEngineTestClientBase,
    setup_test_data,
) -> None:
    """Test successful transform execution against a trace."""
    test_data = setup_test_data

    # Create a dataset
    status_code, dataset = client.create_dataset(
        name="Test Dataset for Transform Execution",
        description="Testing transform execution",
    )
    assert status_code == 200

    try:
        # Create a transform that extracts data from the test spans
        transform_definition = {
            "version": "1.0",
            "columns": [
                {
                    "column_name": "sqlQuery",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "attributes.input.value.sqlQuery",
                    "fallback": None,
                },
                {
                    "column_name": "trace_id",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "traceId",
                    "fallback": None,
                },
                {
                    "column_name": "token_cost",
                    "span_name": "llm_call",
                    "attribute_path": "attributes.llm.token_cost",
                    "fallback": 0,
                },
            ],
        }

        status_code, transform = client.create_transform(
            dataset_id=dataset.id,
            name="Test Transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Execute the transform
        status_code, result = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=transform.id,
            task_id=test_data["task_id"],
            trace_id=test_data["trace_id"],
        )

        assert status_code == 200
        assert result is not None
        assert len(result.rows_extracted) == 1

        row = result.rows_extracted[0]
        assert len(row.data) == 3

        # Verify extracted data
        columns = {col.column_name: col.column_value for col in row.data}
        assert "sqlQuery" in columns
        assert columns["sqlQuery"] == "SELECT * FROM users WHERE id = 1"
        assert "trace_id" in columns
        assert columns["trace_id"] == test_data["trace_id"]
        assert "token_cost" in columns
        assert columns["token_cost"] == "0.05"

    finally:
        client.delete_dataset(dataset.id)


@pytest.mark.unit_tests
def test_execute_transform_with_fallback_values(
    client: GenaiEngineTestClientBase,
    setup_test_data,
) -> None:
    """Test transform execution with fallback values for missing spans/attributes."""
    test_data = setup_test_data

    # Create a dataset
    status_code, dataset = client.create_dataset(
        name="Test Dataset for Fallback Values",
        description="Testing fallback values",
    )
    assert status_code == 200

    try:
        # Create a transform that references non-existent spans and attributes
        transform_definition = {
            "version": "1.0",
            "columns": [
                {
                    "column_name": "nonexistent_span",
                    "span_name": "span-that-does-not-exist",
                    "attribute_path": "attributes.some.path",
                    "fallback": "default_value",
                },
                {
                    "column_name": "nonexistent_attribute",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "attributes.path.that.does.not.exist",
                    "fallback": "fallback_attribute",
                },
                {
                    "column_name": "null_fallback",
                    "span_name": "missing-span",
                    "attribute_path": "attributes.test",
                    "fallback": None,
                },
            ],
        }

        status_code, transform = client.create_transform(
            dataset_id=dataset.id,
            name="Test Transform with Fallbacks",
            definition=transform_definition,
        )
        assert status_code == 200

        # Execute the transform
        status_code, result = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=transform.id,
            task_id=test_data["task_id"],
            trace_id=test_data["trace_id"],
        )

        assert status_code == 200
        assert result is not None
        assert len(result.rows_extracted) == 1

        row = result.rows_extracted[0]
        assert len(row.data) == 3

        # Verify fallback values were used
        columns = {col.column_name: col.column_value for col in row.data}
        assert columns["nonexistent_span"] == "default_value"
        assert columns["nonexistent_attribute"] == "fallback_attribute"
        assert columns["null_fallback"] == ""  # None fallback becomes empty string

    finally:
        client.delete_dataset(dataset.id)


@pytest.mark.unit_tests
def test_execute_transform_missing_transform(
    client: GenaiEngineTestClientBase,
    setup_test_data,
) -> None:
    """Test transform execution with a non-existent transform."""
    test_data = setup_test_data

    # Create a dataset
    status_code, dataset = client.create_dataset(
        name="Test Dataset for Missing Transform",
        description="Testing missing transform error",
    )
    assert status_code == 200

    try:
        fake_transform_id = "00000000-0000-0000-0000-000000000000"

        # Try to execute with non-existent transform
        status_code, error = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=fake_transform_id,
            task_id=test_data["task_id"],
            trace_id=test_data["trace_id"],
        )

        assert status_code == 404
        assert error is not None
        assert "not found" in error.get("detail", "").lower()

    finally:
        client.delete_dataset(dataset.id)


@pytest.mark.unit_tests
def test_execute_transform_missing_trace(
    client: GenaiEngineTestClientBase,
    setup_test_data,
) -> None:
    """Test transform execution with a non-existent trace."""
    test_data = setup_test_data

    # Create a dataset
    status_code, dataset = client.create_dataset(
        name="Test Dataset for Missing Trace",
        description="Testing missing trace error",
    )
    assert status_code == 200

    try:
        # Create a transform
        transform_definition = {
            "version": "1.0",
            "columns": [
                {
                    "column_name": "test_column",
                    "span_name": "test-span",
                    "attribute_path": "attributes.test",
                    "fallback": None,
                },
            ],
        }

        status_code, transform = client.create_transform(
            dataset_id=dataset.id,
            name="Test Transform",
            definition=transform_definition,
        )
        assert status_code == 200

        fake_trace_id = "nonexistent_trace_id"

        # Try to execute with non-existent trace
        status_code, error = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=transform.id,
            task_id=test_data["task_id"],
            trace_id=fake_trace_id,
        )

        assert status_code == 404
        assert error is not None
        assert "not found" in error.get("detail", "").lower()

    finally:
        client.delete_dataset(dataset.id)


@pytest.mark.unit_tests
def test_execute_transform_task_mismatch(
    client: GenaiEngineTestClientBase,
    setup_test_data,
) -> None:
    """Test transform execution when trace doesn't belong to specified task."""
    test_data = setup_test_data

    # Create a dataset
    status_code, dataset = client.create_dataset(
        name="Test Dataset for Task Mismatch",
        description="Testing task mismatch error",
    )
    assert status_code == 200

    try:
        # Create a transform
        transform_definition = {
            "version": "1.0",
            "columns": [
                {
                    "column_name": "test_column",
                    "span_name": "test-span",
                    "attribute_path": "attributes.test",
                    "fallback": None,
                },
            ],
        }

        status_code, transform = client.create_transform(
            dataset_id=dataset.id,
            name="Test Transform",
            definition=transform_definition,
        )
        assert status_code == 200

        wrong_task_id = str(uuid.uuid4())

        # Try to execute with wrong task ID
        status_code, error = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=transform.id,
            task_id=wrong_task_id,
            trace_id=test_data["trace_id"],
        )

        assert status_code == 400
        assert error is not None
        assert "does not belong to task" in error.get("detail", "").lower()

    finally:
        client.delete_dataset(dataset.id)


@pytest.mark.unit_tests
def test_execute_transform_complex_nested_data(
    client: GenaiEngineTestClientBase,
    setup_test_data,
) -> None:
    """Test transform execution with complex nested object extraction."""
    test_data = setup_test_data

    # Create a dataset
    status_code, dataset = client.create_dataset(
        name="Test Dataset for Complex Data",
        description="Testing complex nested data extraction",
    )
    assert status_code == 200

    try:
        # Create a transform that extracts nested JSON data
        transform_definition = {
            "version": "1.0",
            "columns": [
                {
                    "column_name": "query_results",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "attributes.output.value.results",
                    "fallback": [],
                },
                {
                    "column_name": "context",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "attributes.input.value.context",
                    "fallback": None,
                },
            ],
        }

        status_code, transform = client.create_transform(
            dataset_id=dataset.id,
            name="Test Complex Transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Execute the transform
        status_code, result = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=transform.id,
            task_id=test_data["task_id"],
            trace_id=test_data["trace_id"],
        )

        assert status_code == 200
        assert result is not None
        assert len(result.rows_extracted) == 1

        row = result.rows_extracted[0]
        columns = {col.column_name: col.column_value for col in row.data}

        # Verify complex data is JSON stringified
        assert "query_results" in columns
        results = json.loads(columns["query_results"])
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["name"] == "John"

        assert "context" in columns
        assert columns["context"] == "User query context"

    finally:
        client.delete_dataset(dataset.id)


@pytest.mark.unit_tests
def test_execute_transform_with_multiple_matching_spans(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test that transform uses first matching span when multiple spans match."""
    db_session: Session = override_get_db_session()
    span_normalizer = SpanNormalizationService()

    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    # Create task
    task = DatabaseTask(
        id=task_id,
        name="Test Task",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(task)
    db_session.commit()

    base_time = datetime.now()

    # Create multiple spans with the same name but different values
    spans_data = []
    for i in range(3):
        span_raw_data = span_normalizer.normalize_span_to_nested_dict(
            {
                "kind": "SPAN_KIND_INTERNAL",
                "name": "duplicate_span",
                "spanId": f"span_{i}_{uuid.uuid4()}",
                "traceId": trace_id,
                "attributes": {
                    "openinference.span.kind": "RETRIEVER",
                    "test.value": f"value_{i}",
                },
            },
        )
        span_raw_data["arthur_span_version"] = "arthur_span_v1"

        span = InternalSpan(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            span_id=span_raw_data["spanId"],
            task_id=task_id,
            parent_span_id=None,
            span_kind="RETRIEVER",
            start_time=base_time,
            end_time=base_time,
            session_id=None,
            user_id=None,
            raw_data=span_raw_data,
            created_at=base_time,
            updated_at=base_time,
        )
        spans_data.append(span)

        db_span = DatabaseSpan(
            id=span.id,
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            span_name=span.raw_data.get("name"),
            span_kind=span.span_kind,
            start_time=span.start_time,
            end_time=span.end_time,
            task_id=span.task_id,
            session_id=span.session_id,
            user_id=span.user_id,
            status_code="Ok",
            raw_data=span.raw_data,
            created_at=span.created_at,
            updated_at=span.updated_at,
        )
        db_session.add(db_span)

    db_session.commit()

    # Create trace metadata
    trace_metadata = DatabaseTraceMetadata(
        task_id=task_id,
        trace_id=trace_id,
        session_id=None,
        user_id=None,
        span_count=len(spans_data),
        start_time=base_time,
        end_time=base_time,
        created_at=base_time,
        updated_at=base_time,
    )
    db_session.add(trace_metadata)
    db_session.commit()

    try:
        # Create a dataset and transform
        status_code, dataset = client.create_dataset(
            name="Test Dataset for Duplicate Spans",
            description="Testing first match selection",
        )
        assert status_code == 200

        transform_definition = {
            "version": "1.0",
            "columns": [
                {
                    "column_name": "extracted_value",
                    "span_name": "duplicate_span",
                    "attribute_path": "attributes.test.value",
                    "fallback": None,
                },
            ],
        }

        status_code, transform = client.create_transform(
            dataset_id=dataset.id,
            name="Test Transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Execute the transform
        status_code, result = client.execute_transform_extraction(
            dataset_id=dataset.id,
            transform_id=transform.id,
            task_id=task_id,
            trace_id=trace_id,
        )

        assert status_code == 200
        assert result is not None
        assert len(result.rows_extracted) == 1

        row = result.rows_extracted[0]
        columns = {col.column_name: col.column_value for col in row.data}

        # Should use value from the first matching span
        assert "extracted_value" in columns
        assert columns["extracted_value"] == "value_0"

        client.delete_dataset(dataset.id)

    finally:
        # Cleanup
        db_session.query(DatabaseSpan).filter(DatabaseSpan.trace_id == trace_id).delete()
        db_session.query(DatabaseTraceMetadata).filter(
            DatabaseTraceMetadata.trace_id == trace_id,
        ).delete()
        db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
        db_session.commit()
