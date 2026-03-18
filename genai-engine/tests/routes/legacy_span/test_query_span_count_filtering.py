"""Tests for filtering traces by span_count (number of spans per trace)."""

import uuid
from datetime import datetime, timedelta
from typing import Generator

import pytest

from db_models import (
    DatabaseSpan,
    DatabaseTask,
    DatabaseTraceMetadata,
)
from schemas.internal_schemas import Span as InternalSpan
from services.trace.span_normalization_service import SpanNormalizationService
from tests.clients.base_test_client import GenaiEngineTestClientBase, override_get_db_session


def _make_span(
    span_normalizer: SpanNormalizationService,
    trace_id: str,
    span_id: str,
    task_id: str,
    start_time: datetime,
    span_kind: str = "LLM",
    parent_span_id: str | None = None,
) -> InternalSpan:
    raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": f"Span_{span_id}",
            "spanId": span_id,
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": span_kind,
                "metadata": '{"ls_provider": "openai"}',
            },
        },
    )
    raw_data["arthur_span_version"] = "arthur_span_v1"
    return InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span_id,
        task_id=task_id,
        parent_span_id=parent_span_id,
        span_kind=span_kind,
        start_time=start_time,
        end_time=start_time + timedelta(seconds=1),
        raw_data=raw_data,
        created_at=start_time + timedelta(seconds=1),
        updated_at=start_time + timedelta(seconds=1),
    )


@pytest.fixture(scope="function")
def spans_with_varied_counts() -> Generator:
    """Create traces with different span counts for filtering tests.

    trace_a (task_x): 1 span  -> span_count=1
    trace_b (task_x): 3 spans -> span_count=3
    trace_c (task_x): 5 spans -> span_count=5
    """
    db_session = override_get_db_session()
    span_normalizer = SpanNormalizationService()
    base_time = datetime.now()

    spans: list[InternalSpan] = []

    # trace_a: 1 span
    spans.append(_make_span(span_normalizer, "trace_a", "sa1", "task_x", base_time))

    # trace_b: 3 spans
    spans.append(_make_span(span_normalizer, "trace_b", "sb1", "task_x", base_time + timedelta(hours=1)))
    spans.append(_make_span(span_normalizer, "trace_b", "sb2", "task_x", base_time + timedelta(hours=1, seconds=2), parent_span_id="sb1"))
    spans.append(_make_span(span_normalizer, "trace_b", "sb3", "task_x", base_time + timedelta(hours=1, seconds=4), parent_span_id="sb1"))

    # trace_c: 5 spans
    spans.append(_make_span(span_normalizer, "trace_c", "sc1", "task_x", base_time + timedelta(hours=2)))
    spans.append(_make_span(span_normalizer, "trace_c", "sc2", "task_x", base_time + timedelta(hours=2, seconds=2), parent_span_id="sc1"))
    spans.append(_make_span(span_normalizer, "trace_c", "sc3", "task_x", base_time + timedelta(hours=2, seconds=4), parent_span_id="sc1"))
    spans.append(_make_span(span_normalizer, "trace_c", "sc4", "task_x", base_time + timedelta(hours=2, seconds=6), parent_span_id="sc1"))
    spans.append(_make_span(span_normalizer, "trace_c", "sc5", "task_x", base_time + timedelta(hours=2, seconds=8), parent_span_id="sc1"))

    database_spans = [
        DatabaseSpan(
            id=s.id,
            trace_id=s.trace_id,
            span_id=s.span_id,
            parent_span_id=s.parent_span_id,
            span_name=s.raw_data.get("name"),
            span_kind=s.span_kind,
            start_time=s.start_time,
            end_time=s.end_time,
            task_id=s.task_id,
            raw_data=s.raw_data,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in spans
    ]
    db_session.add_all(database_spans)
    db_session.commit()

    trace_configs = {
        "trace_a": {"span_count": 1, "total_token_count": 100},
        "trace_b": {"span_count": 3, "total_token_count": 500},
        "trace_c": {"span_count": 5, "total_token_count": 1000},
    }
    for trace_id, cfg in trace_configs.items():
        trace_spans = [s for s in spans if s.trace_id == trace_id]
        db_session.add(
            DatabaseTraceMetadata(
                task_id="task_x",
                trace_id=trace_id,
                span_count=cfg["span_count"],
                total_token_count=cfg["total_token_count"],
                start_time=min(s.start_time for s in trace_spans),
                end_time=max(s.end_time for s in trace_spans),
                created_at=min(s.start_time for s in trace_spans),
                updated_at=max(s.end_time for s in trace_spans),
            ),
        )

    task = DatabaseTask(id="task_x", name="Test Task X", created_at=base_time, updated_at=base_time)
    db_session.add(task)
    db_session.commit()

    yield spans

    db_session.query(DatabaseSpan).filter(
        DatabaseSpan.span_id.in_([s.span_id for s in spans]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(list(trace_configs.keys())),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTask).filter(DatabaseTask.id == "task_x").delete(synchronize_session=False)
    db_session.commit()


# ============================================================================
# SPAN COUNT FILTERING - gte / lte
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_gte(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Filter traces where span_count >= 3 -> trace_b (3) and trace_c (5)."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_gte=3)
    assert status_code == 200
    assert response.count == 2
    assert {t.trace_id for t in response.traces} == {"trace_b", "trace_c"}


@pytest.mark.unit_tests
def test_span_count_lte(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Filter traces where span_count <= 3 -> trace_a (1) and trace_b (3)."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_lte=3)
    assert status_code == 200
    assert response.count == 2
    assert {t.trace_id for t in response.traces} == {"trace_a", "trace_b"}


# ============================================================================
# SPAN COUNT FILTERING - gt / lt
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_gt(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Filter traces where span_count > 3 -> only trace_c (5)."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_gt=3)
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace_c"


@pytest.mark.unit_tests
def test_span_count_lt(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Filter traces where span_count < 3 -> only trace_a (1)."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_lt=3)
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace_a"


# ============================================================================
# SPAN COUNT FILTERING - eq
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_eq(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Filter traces where span_count == 3 -> only trace_b."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_eq=3)
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace_b"


# ============================================================================
# SPAN COUNT FILTERING - range
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_range(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Filter with min/max range: 2 <= span_count <= 4 -> only trace_b (3)."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_gte=2, span_count_lte=4)
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace_b"


# ============================================================================
# SPAN COUNT FILTERING - no results
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_no_results(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Span count threshold that excludes all traces."""
    status_code, response = client.query_traces(task_ids=["task_x"], span_count_gte=100)
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


# ============================================================================
# SPAN COUNT FILTERING - combined with other filters
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_with_token_count_filter(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Combine span_count and total_token_count filters."""
    # span_count >= 3 gives trace_b (500 tokens) and trace_c (1000 tokens)
    # total_token_count <= 500 narrows to trace_b only
    status_code, response = client.query_traces(
        task_ids=["task_x"],
        span_count_gte=3,
        total_token_count_lte=500,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace_b"


# ============================================================================
# SPAN COUNT FILTERING - metrics endpoint
# ============================================================================


@pytest.mark.unit_tests
def test_span_count_on_metrics_endpoint(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Verify span_count filters work on the /v1/traces/metrics/ endpoint."""
    status_code, response = client.query_traces_with_metrics(task_ids=["task_x"], span_count_gte=5)
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace_c"


# ============================================================================
# SPAN COUNT SORTING - with varied span counts
# ============================================================================


@pytest.mark.unit_tests
def test_sort_by_span_count_ascending_varied(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Sort by span_count ascending: trace_a (1) < trace_b (3) < trace_c (5)."""
    status_code, response = client.query_traces(task_ids=["task_x"], sort="asc", sort_by="span_count")
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace_a", "trace_b", "trace_c"]


@pytest.mark.unit_tests
def test_sort_by_span_count_descending_varied(client: GenaiEngineTestClientBase, spans_with_varied_counts):
    """Sort by span_count descending: trace_c (5) > trace_b (3) > trace_a (1)."""
    status_code, response = client.query_traces(task_ids=["task_x"], sort="desc", sort_by="span_count")
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace_c", "trace_b", "trace_a"]
