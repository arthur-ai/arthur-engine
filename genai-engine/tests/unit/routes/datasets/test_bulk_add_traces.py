"""Tests for the bulk-add-traces-to-dataset endpoint."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from db_models import DatabaseSpan, DatabaseTask, DatabaseTraceMetadata
from schemas.common_schemas import NewDatasetVersionRowColumnItemRequest
from schemas.internal_schemas import Span as InternalSpan
from schemas.request_schemas import NewDatasetVersionRowRequest
from services.trace.span_normalization_service import SpanNormalizationService
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from utils.constants import DEFAULT_ORG_ID, MAX_BULK_ADD_TRACES


@pytest.fixture(scope="function")
def setup_trace():
    """Create a task, a trace and its spans for transform extraction."""
    db_session: Session = override_get_db_session()
    span_normalizer = SpanNormalizationService()

    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    base_time = datetime.now()

    task = DatabaseTask(
        id=task_id,
        name="Test Task for Bulk Add Traces",
        created_at=base_time,
        updated_at=base_time,
        org_id=DEFAULT_ORG_ID,
    )
    db_session.add(task)
    db_session.commit()

    span1_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "rag-retrieval-savedQueries",
            "spanId": f"span1_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "RETRIEVER",
                "input.value.sqlQuery": "SELECT * FROM users WHERE id = 1",
            },
        },
    )
    span1_raw_data["arthur_span_version"] = "arthur_span_v1"

    span2_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "llm_call",
            "spanId": f"span2_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.token_cost": 0.05,
            },
        },
    )
    span2_raw_data["arthur_span_version"] = "arthur_span_v1"

    spans = []
    for raw_data, kind in ((span1_raw_data, "RETRIEVER"), (span2_raw_data, "LLM")):
        span = InternalSpan(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            span_id=raw_data["spanId"],
            task_id=task_id,
            parent_span_id=None,
            span_kind=kind,
            start_time=base_time,
            end_time=base_time,
            session_id=None,
            user_id=None,
            raw_data=raw_data,
            created_at=base_time,
            updated_at=base_time,
        )
        spans.append(span)

    database_spans = [
        DatabaseSpan(
            id=span.id,
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            span_name=span.raw_data.get("name"),
            span_kind=span.span_kind,
            start_time=span.start_time,
            end_time=span.end_time,
            task_id=span.task_id,
            org_id=DEFAULT_ORG_ID,
            session_id=span.session_id,
            user_id=span.user_id,
            status_code="Ok",
            raw_data=span.raw_data,
            created_at=span.created_at,
            updated_at=span.updated_at,
        )
        for span in spans
    ]
    db_session.add_all(database_spans)
    db_session.commit()

    trace_metadata = DatabaseTraceMetadata(
        task_id=task_id,
        org_id=DEFAULT_ORG_ID,
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

    yield {"task_id": task_id, "trace_id": trace_id, "db_session": db_session}

    db_session.query(DatabaseSpan).filter(DatabaseSpan.trace_id == trace_id).delete()
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id == trace_id,
    ).delete()
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
    db_session.commit()


def _extraction_transform_definition() -> dict:
    return {
        "variables": [
            {
                "variable_name": "sqlQuery",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.sqlQuery",
                "fallback": None,
            },
            {
                "variable_name": "token_cost",
                "span_name": "llm_call",
                "attribute_path": "attributes.llm.token_cost",
                "fallback": "0",
            },
        ],
    }


@pytest.mark.unit_tests
def test_bulk_add_traces_all_success_with_existing_schema(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """All traces succeed and rows are written onto the dataset's existing columns."""
    trace_id = setup_trace["trace_id"]

    status_code, task = client.create_task(
        name="bulk_add_all_success_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        # Seed the dataset with a version so it has a column schema.
        status_code, _ = client.create_dataset_version(
            dataset_id=dataset.id,
            rows_to_add=[
                NewDatasetVersionRowRequest(
                    data=[
                        NewDatasetVersionRowColumnItemRequest(
                            column_name="sqlQuery",
                            column_value="seed",
                        ),
                        NewDatasetVersionRowColumnItemRequest(
                            column_name="token_cost",
                            column_value="seed",
                        ),
                    ],
                ),
            ],
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=[trace_id],
        )

        assert status_code == 200, result
        assert result.success_count == 1
        assert result.total == 1
        assert len(result.results) == 1
        assert result.results[0].trace_id == trace_id
        assert result.results[0].success is True
        assert result.results[0].error is None

        # Verify the new row was persisted with the extracted values.
        status_code, latest = client.get_dataset_version(
            dataset_id=dataset.id,
            version_number=2,
        )
        assert status_code == 200
        extracted_rows = [
            {item.column_name: item.column_value for item in row.data}
            for row in latest.rows
        ]
        matching = [
            r
            for r in extracted_rows
            if r.get("sqlQuery") == "SELECT * FROM users WHERE id = 1"
        ]
        assert len(matching) == 1
        assert matching[0]["token_cost"] == "0.05"

        # The bulk-added row records its originating trace; the seed row does not.
        rows_by_trace_id = {row.trace_id: row for row in latest.rows}
        assert set(rows_by_trace_id) == {trace_id, None}
        bulk_added_row_data = {
            item.column_name: item.column_value
            for item in rows_by_trace_id[trace_id].data
        }
        assert bulk_added_row_data["sqlQuery"] == "SELECT * FROM users WHERE id = 1"
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_empty_fields_missing_spans(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """A trace with no matching span still succeeds; missing extraction -> empty string.

    Also exercises the fallback where the dataset has no version yet: columns are
    taken from the transform definition's variable names.
    """
    trace_id = setup_trace["trace_id"]

    status_code, task = client.create_task(
        name="bulk_add_empty_fields_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        # Fresh dataset with no version -> empty schema -> fallback to transform vars.
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-empty-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        transform_definition = {
            "variables": [
                {
                    "variable_name": "missing_field",
                    "span_name": "span-that-does-not-exist",
                    "attribute_path": "attributes.some.path",
                    "fallback": None,
                },
            ],
        }
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_missing_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=[trace_id],
        )

        assert status_code == 200, result
        assert result.success_count == 1
        assert result.total == 1
        assert result.results[0].success is True

        # Columns fell back to transform variable names; value is empty.
        status_code, latest = client.get_dataset_version(
            dataset_id=dataset.id,
            version_number=1,
        )
        assert status_code == 200
        assert "missing_field" in latest.column_names
        assert len(latest.rows) == 1
        row = {item.column_name: item.column_value for item in latest.rows[0].data}
        assert row["missing_field"] == ""
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_partial_trace_not_found(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """A missing trace is reported as a failure while valid traces still succeed."""
    trace_id = setup_trace["trace_id"]
    missing_trace_id = f"nonexistent-{uuid.uuid4()}"

    status_code, task = client.create_task(
        name="bulk_add_partial_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-partial-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_partial_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=[trace_id, missing_trace_id],
        )

        assert status_code == 200, result
        assert result.total == 2
        assert result.success_count == 1

        results_by_trace = {r.trace_id: r for r in result.results}
        assert results_by_trace[trace_id].success is True
        assert results_by_trace[missing_trace_id].success is False
        assert results_by_trace[missing_trace_id].error == "trace not found"
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_unknown_transform_404(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """An unknown transform ID returns a 404."""
    trace_id = setup_trace["trace_id"]

    status_code, task = client.create_task(
        name="bulk_add_unknown_transform_task",
        is_agentic=True,
    )
    assert status_code == 200

    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-unknown-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        status_code, error = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id="00000000-0000-0000-0000-000000000000",
            trace_ids=[trace_id],
        )

        assert status_code == 404
        assert error is not None
        assert "not found" in error.get("detail", "").lower()
    finally:
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_too_many_trace_ids_422(
    client: GenaiEngineTestClientBase,
) -> None:
    """Exceeding MAX_BULK_ADD_TRACES returns a 422."""
    status_code, task = client.create_task(
        name="bulk_add_too_many_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-too-many-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_too_many_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        trace_ids = [f"trace-{i}" for i in range(MAX_BULK_ADD_TRACES + 1)]
        status_code, error = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=trace_ids,
        )

        assert status_code == 422
        assert error is not None
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_exactly_max_succeeds(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """Exactly MAX_BULK_ADD_TRACES trace_ids is accepted (200, not 422) at the cap boundary."""
    trace_id = setup_trace["trace_id"]

    status_code, task = client.create_task(
        name="bulk_add_exactly_max_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-exactly-max-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_exactly_max_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        # One real trace plus enough distinct fake IDs to hit the cap exactly.
        trace_ids = [trace_id] + [
            f"trace-{uuid.uuid4()}" for _ in range(MAX_BULK_ADD_TRACES - 1)
        ]
        assert len(trace_ids) == MAX_BULK_ADD_TRACES

        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=trace_ids,
        )

        assert status_code == 200, result
        assert result.total == MAX_BULK_ADD_TRACES
        assert len(result.results) == MAX_BULK_ADD_TRACES
        # The single real trace succeeds; the fake ones are reported as failures.
        assert result.success_count == 1
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_all_fail_success_count_zero(
    client: GenaiEngineTestClientBase,
) -> None:
    """A batch where every trace is missing returns success_count == 0 (drives the FE error toast)."""
    status_code, task = client.create_task(
        name="bulk_add_all_fail_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-all-fail-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_all_fail_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        missing_trace_ids = [f"nonexistent-{uuid.uuid4()}" for _ in range(3)]
        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=missing_trace_ids,
        )

        assert status_code == 200, result
        assert result.success_count == 0
        assert result.total == 3
        assert len(result.results) == 3
        assert all(r.success is False for r in result.results)
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_deduplicates_trace_ids(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """Duplicate trace_ids are deduped server-side; counts/rows reflect unique traces."""
    trace_id = setup_trace["trace_id"]

    status_code, task = client.create_task(
        name="bulk_add_dedupe_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-dedupe-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        # Seed the dataset with a version so it has a column schema.
        status_code, _ = client.create_dataset_version(
            dataset_id=dataset.id,
            rows_to_add=[
                NewDatasetVersionRowRequest(
                    data=[
                        NewDatasetVersionRowColumnItemRequest(
                            column_name="sqlQuery",
                            column_value="seed",
                        ),
                        NewDatasetVersionRowColumnItemRequest(
                            column_name="token_cost",
                            column_value="seed",
                        ),
                    ],
                ),
            ],
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_dedupe_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        # Same trace ID repeated three times -> should be deduped to a single trace.
        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=[trace_id, trace_id, trace_id],
        )

        assert status_code == 200, result
        assert result.total == 1
        assert result.success_count == 1
        assert len(result.results) == 1
        assert result.results[0].trace_id == trace_id

        # Only one new row was persisted (unique trace), on top of the seed row.
        status_code, latest = client.get_dataset_version(
            dataset_id=dataset.id,
            version_number=2,
        )
        assert status_code == 200
        matching = [
            row
            for row in latest.rows
            if {item.column_name: item.column_value for item in row.data}.get(
                "sqlQuery"
            )
            == "SELECT * FROM users WHERE id = 1"
        ]
        assert len(matching) == 1
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_unknown_dataset_404(
    client: GenaiEngineTestClientBase,
    setup_trace,
) -> None:
    """A non-existent (or cross-org) dataset returns 404 up front, not a 200 with success_count=0."""
    trace_id = setup_trace["trace_id"]

    status_code, task = client.create_task(
        name="bulk_add_unknown_dataset_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_unknown_dataset_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        unknown_dataset_id = str(uuid.uuid4())
        status_code, error = client.bulk_add_traces_to_dataset(
            dataset_id=unknown_dataset_id,
            transform_id=transform.id,
            trace_ids=[trace_id],
        )

        assert status_code == 404
        assert error is not None
        assert "not found" in error.get("detail", "").lower()
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_bulk_add_traces_empty_trace_ids(
    client: GenaiEngineTestClientBase,
) -> None:
    """An empty trace_ids list is handled gracefully with zero counts."""
    status_code, task = client.create_task(
        name="bulk_add_empty_task",
        is_agentic=True,
    )
    assert status_code == 200

    transform = None
    dataset = None
    try:
        status_code, dataset = client.create_dataset(
            name=f"bulk-add-empty-list-dataset-{uuid.uuid4()}",
            task_id=task.id,
        )
        assert status_code == 200

        status_code, transform = client.create_transform(
            task_id=task.id,
            name="bulk_add_empty_transform",
            definition=_extraction_transform_definition(),
        )
        assert status_code == 200

        status_code, result = client.bulk_add_traces_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
            trace_ids=[],
        )

        assert status_code == 200, result
        assert result.success_count == 0
        assert result.total == 0
        assert result.results == []
    finally:
        if transform is not None:
            client.delete_transform(transform.id)
        if dataset is not None:
            client.delete_dataset(dataset.id)
        assert client.delete_task(task.id) == 204
