import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod

from db_models import DatabaseSpan, DatabaseTask, DatabaseTraceMetadata
from db_models.organization_models import DatabaseOrganization
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.conftest import (
    _create_base_trace_request,
    _create_span,
)
from utils.constants import AGENT_EXPERIMENT_SESSION_PREFIX

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def assert_valid_session_metadata_response(sessions):
    """Assert response has valid session metadata structure."""
    for session in sessions:
        assert session.session_id and isinstance(session.session_id, str)
        assert session.task_id and isinstance(session.task_id, str)
        assert session.user_id is not None  # Should have user_id
        assert (
            session.span_count is not None
            and isinstance(session.span_count, int)
            and session.span_count >= 0
        )
        assert session.earliest_start_time is not None
        assert session.latest_end_time is not None
        # Verify token count/cost fields are present (may be None if no LLM spans)
        assert hasattr(session, "prompt_token_count")
        assert hasattr(session, "completion_token_count")
        assert hasattr(session, "total_token_count")
        assert hasattr(session, "prompt_token_cost")
        assert hasattr(session, "completion_token_cost")
        assert hasattr(session, "total_token_cost")


def assert_valid_session_traces_response(traces):
    """Assert response has valid session traces structure."""
    for trace in traces:
        assert trace.trace_id and isinstance(trace.trace_id, str)
        assert trace.start_time is not None
        assert trace.end_time is not None
        assert hasattr(trace, "root_spans") and isinstance(trace.root_spans, list)


def get_all_spans_from_traces(traces):
    """Helper function to extract all spans from traces response."""
    spans = []
    for trace in traces:
        for root_span in trace.root_spans:
            spans.extend(get_all_spans_from_nested_span(root_span))
    return spans


def get_all_spans_from_nested_span(nested_span):
    """Helper function to extract all spans from a nested span structure recursively."""
    spans = [nested_span]
    for child in getattr(nested_span, "children", []):
        spans.extend(get_all_spans_from_nested_span(child))
    return spans


def find_spans_by_kind(spans, span_kind):
    """Helper function to find all spans matching the given kind."""
    return [span for span in spans if getattr(span, "span_kind", None) == span_kind]


# ============================================================================
# SESSION METADATA LIST TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_list_sessions_metadata_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session metadata listing functionality for single and multiple tasks."""

    # Test single task
    status_code, data = client.trace_api_list_sessions_metadata(task_ids=["api_task1"])
    assert status_code == 200
    assert data.count == 1  # Only session1 has api_task1 traces
    assert len(data.sessions) == 1

    # Verify session metadata structure
    assert_valid_session_metadata_response(data.sessions)

    session = data.sessions[0]
    assert session.session_id == "session1"
    assert session.task_id == "api_task1"
    assert session.span_count > 0
    assert session.earliest_start_time is not None
    assert session.latest_end_time is not None
    # Session1 has api_trace1 (span1: 100/50/150, span2: None) and api_trace2 (span3: 200/100/300)
    # Total: 300 prompt, 150 completion, 450 total
    assert session.prompt_token_count == 300
    assert session.completion_token_count == 150
    assert session.total_token_count == 450
    assert session.prompt_token_cost == 0.003  # 0.001 + 0.002
    assert session.completion_token_cost == 0.005  # 0.002 + 0.003
    assert session.total_token_cost == 0.008  # 0.003 + 0.005

    # Test multiple tasks
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    assert data.count == 2  # session1 (api_task1) and session2 (api_task2)
    assert len(data.sessions) == 2

    # Verify we have sessions from both tasks
    session_data = {(s.session_id, s.task_id) for s in data.sessions}
    expected_sessions = {("session1", "api_task1"), ("session2", "api_task2")}
    assert session_data == expected_sessions


@pytest.mark.unit_tests
def test_list_sessions_metadata_filtering_by_user_ids(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test filtering sessions by user IDs with substring matching."""

    # Filter sessions by user1
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
        user_ids=["user1"],
    )
    assert status_code == 200
    assert data.count == 1  # user1 has 1 session in api_task1
    assert len(data.sessions) == 1

    # Verify session belongs to user1
    session = data.sessions[0]
    assert session.user_id == "user1"
    assert session.task_id == "api_task1"
    assert session.session_id == "session1"

    # Filter by multiple users
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
        user_ids=["user1", "user2"],
    )
    assert status_code == 200
    assert data.count == 2  # user1 has 1 session, user2 has 1 session
    assert len(data.sessions) == 2

    # Verify we have sessions from both users
    user_ids = {session.user_id for session in data.sessions}
    assert user_ids == {"user1", "user2"}

    # Substring match: "user" matches both "user1" and "user2"
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
        user_ids=["user"],
    )
    assert status_code == 200
    assert data.count == 2
    matched_user_ids = {session.user_id for session in data.sessions}
    assert matched_user_ids == {"user1", "user2"}

    # Case-insensitive match: "USER1" should match "user1"
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
        user_ids=["USER1"],
    )
    assert status_code == 200
    assert data.count == 1
    assert data.sessions[0].user_id == "user1"

    # Filter by non-existent user
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
        user_ids=["non_existent_user"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.sessions) == 0


@pytest.mark.unit_tests
def test_list_sessions_metadata_sorting_pagination_and_validation(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session metadata sorting, pagination, and validation."""

    # Test default sorting (descending)
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    sessions = data.sessions

    # Verify descending order (most recent first)
    for i in range(len(sessions) - 1):
        current_time = sessions[i].earliest_start_time
        next_time = sessions[i + 1].earliest_start_time
        assert current_time >= next_time

    # Test pagination
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
        page=0,
        page_size=1,
    )
    assert status_code == 200
    assert data.count == 2  # Total count
    assert len(data.sessions) == 1  # Page size

    # Test validation errors
    # Empty task_ids (should return 400)
    status_code, response = client.trace_api_list_sessions_metadata(task_ids=[])
    assert status_code == 400

    # Non-existent task (should return 200 with 0 results)
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.sessions) == 0


@pytest.mark.unit_tests
def test_list_sessions_metadata_empty_results(
    client: GenaiEngineTestClientBase,
):
    """Test listing sessions with no results."""

    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.sessions) == 0


# ============================================================================
# SESSION TRACES RETRIEVAL TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_session_traces_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test retrieving traces for a specific session."""

    # Get traces for session1
    status_code, data = client.trace_api_get_session_traces("session1")
    assert status_code == 200
    assert data.session_id == "session1"
    assert data.count == 2  # session1 has 2 traces (api_trace1, api_trace2)
    assert len(data.traces) == 2

    # Verify traces structure
    assert_valid_session_traces_response(data.traces)

    # Verify all traces belong to session1
    for trace in data.traces:
        # Get all spans to check session_id
        all_spans = get_all_spans_from_traces([trace])
        for span in all_spans:
            if getattr(
                span,
                "session_id",
                None,
            ):  # Some spans might not have session_id
                assert span.session_id == "session1"


@pytest.mark.unit_tests
def test_get_session_traces_with_existing_metrics(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session traces include existing metrics but don't compute new ones."""

    status_code, data = client.trace_api_get_session_traces("session1")
    assert status_code == 200
    all_spans = get_all_spans_from_traces(data.traces)

    # Find LLM spans which should have metrics
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) >= 1

    for llm_span in llm_spans:
        assert hasattr(
            llm_span,
            "metric_results",
        )  # Field exists, but may be None or list
        # May or may not have existing metrics depending on span


@pytest.mark.unit_tests
def test_get_session_traces_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test retrieving traces for non-existent session returns 404."""

    status_code, response_data = client.trace_api_get_session_traces(
        "non_existent_session",
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


@pytest.mark.unit_tests
def test_get_session_traces_nested_structure(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session traces have proper nested structure."""

    status_code, data = client.trace_api_get_session_traces("session1")
    assert status_code == 200

    # Find trace1 which has nested structure
    trace1 = next((t for t in data.traces if t.trace_id == "api_trace1"), None)
    assert trace1 is not None

    # Verify nested structure
    assert len(trace1.root_spans) == 1
    root_span = trace1.root_spans[0]

    assert root_span.span_id == "api_span1"
    assert root_span.span_kind == "LLM"
    assert len(root_span.children) == 1

    child_span = root_span.children[0]
    assert child_span.span_id == "api_span2"
    assert child_span.span_kind == "CHAIN"
    assert child_span.parent_span_id == "api_span1"


# ============================================================================
# COMPUTE SESSION METRICS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_compute_session_metrics_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test computing missing metrics for session traces."""

    status_code, data = client.trace_api_compute_session_metrics("session1")
    assert status_code == 200
    assert data.session_id == "session1"
    assert data.count == 2  # Same number of traces

    # Verify structure is the same as regular session traces
    assert_valid_session_traces_response(data.traces)


@pytest.mark.unit_tests
def test_compute_session_metrics_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test computing metrics for non-existent session returns 404."""

    status_code, response_data = client.trace_api_compute_session_metrics(
        "non_existent_session",
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit_tests
def test_session_api_error_handling(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test various error conditions in session API."""

    # Test server error in session metadata listing
    with patch(
        "repositories.span_repository.SpanRepository.get_sessions_metadata",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_list_sessions_metadata(task_ids=["api_task1"])
        assert status_code == 500

    # Test server error in session traces retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_session_traces",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_session_traces("session1")
        assert status_code == 500


@pytest.mark.unit_tests
def test_session_aggregation_consistency(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test consistency between session metadata and actual session traces."""

    # Get session metadata
    status_code, sessions_response = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    session_metadata = sessions_response.sessions[0]
    session_id = session_metadata.session_id

    # Get actual session traces
    status_code, session_traces = client.trace_api_get_session_traces(session_id)
    assert status_code == 200

    # Verify consistency
    actual_trace_count = session_traces.count
    expected_span_count = session_metadata.span_count

    # Count actual spans in traces
    all_spans = get_all_spans_from_traces(session_traces.traces)
    actual_span_count = len(all_spans)

    assert actual_span_count == expected_span_count


@pytest.mark.unit_tests
def test_experiment_sessions_excluded_from_session_endpoint(
    client: GenaiEngineTestClientBase,
):
    """Test that experiment sessions are excluded from session endpoint by default."""

    # Create a regular trace with regular session
    regular_trace_request, regular_resource_span, regular_scope_span = (
        _create_base_trace_request(task_id="exp_test_task")
    )
    regular_span = _create_span(
        trace_id=b"regular_trace_session",
        span_id=b"regular_span_session",
        name="RegularSpan",
        span_type="LLM",
        session_id="regular_session_test",
    )
    regular_scope_span.spans.append(regular_span)
    regular_resource_span.scope_spans.append(regular_scope_span)
    regular_trace_request.resource_spans.append(regular_resource_span)

    # Create an experiment trace (with session_id starting with AGENT_EXPERIMENT_SESSION_PREFIX)
    experiment_session_id = f"{AGENT_EXPERIMENT_SESSION_PREFIX}-test-789"
    experiment_trace_request, experiment_resource_span, experiment_scope_span = (
        _create_base_trace_request(task_id="exp_test_task")
    )
    experiment_span = _create_span(
        trace_id=b"experiment_trace_session",
        span_id=b"experiment_span_session",
        name="ExperimentSpan",
        span_type="LLM",
        session_id=experiment_session_id,
    )
    experiment_scope_span.spans.append(experiment_span)
    experiment_resource_span.scope_spans.append(experiment_scope_span)
    experiment_trace_request.resource_spans.append(experiment_resource_span)

    # Send both traces via upload endpoint
    status_code1, _ = client.trace_api_receive_traces(
        regular_trace_request.SerializeToString(),
    )
    status_code2, _ = client.trace_api_receive_traces(
        experiment_trace_request.SerializeToString(),
    )

    assert status_code1 == 200, "Regular trace should be accepted"
    assert status_code2 == 200, "Experiment trace should be accepted"

    # Query sessions - should only return the regular session (experiment session excluded by default)
    status_code, response = client.trace_api_list_sessions_metadata(
        task_ids=["exp_test_task"],
    )
    assert status_code == 200

    # Verify only regular session is returned
    session_ids = {session.session_id for session in response.sessions}
    assert "regular_session_test" in session_ids, "Regular session should be included"
    assert (
        experiment_session_id not in session_ids
    ), "Experiment session should be excluded by default"


# ============================================================================
# CROSS-ORG PAGINATION TESTS (org_scope pushed into SQL layer)
# ============================================================================
#
# These regression tests pin the multi-tenant pagination behavior fixed in
# PR #1693. Before the fix, SpanRepository.get_session_traces (and the
# parallel compute_session_metrics) asked span_query_service for an
# unfiltered (count, page_slice) and then post-filtered that page slice by
# org_id. That produced three concrete failure modes for tenant callers:
#   1. count reflected page-size-after-filter, not the total org-owned count
#   2. later pages returned 0 traces (route handler raises 404) even though
#      org-owned traces existed further into the result set
#   3. pages were partially populated (page_size=N, fewer than N returned)
#
# The fix pushes the org filter into the SQL WHERE clause shared by both the
# count query and the paginated SELECT. The tests below seed a single
# `session_id` populated by two orgs and assert each of those failure modes
# can no longer recur.


@pytest.fixture(scope="function")
def cross_org_session():
    """Seed one session_id containing traces from two distinct orgs.

    Layout:
        org1 ──► task1 ──► 6 traces (O1_t0 .. O1_t5)  shared session
        org2 ──► task2 ──► 4 traces (O2_t0 .. O2_t3)  shared session

    Traces are interleaved in time so descending-sort by start_time
    places one O2 trace at the front, then alternates. This guarantees
    that under page_size=2 DESC sort, page 0 is mixed/O2-heavy and an
    org-scoped caller has to advance pages to see all of its data.

    The shared session_id ensures both orgs land on the same code path
    inside SpanRepository.get_session_traces — the exact spot the buggy
    post-filter used to live.
    """
    db = override_get_db_session()
    suffix = uuid.uuid4().hex[:8]
    session_id = f"mt-session-{suffix}"
    org1_id = uuid.uuid4()
    org2_id = uuid.uuid4()
    task1_id = f"mt-task1-{suffix}"
    task2_id = f"mt-task2-{suffix}"

    now = datetime.now()
    base_time = now - timedelta(hours=1)

    # Orgs
    db.add(
        DatabaseOrganization(
            id=org1_id,
            name=f"mt-org1-{suffix}",
            is_system=False,
            created_at=now,
        ),
    )
    db.add(
        DatabaseOrganization(
            id=org2_id,
            name=f"mt-org2-{suffix}",
            is_system=False,
            created_at=now,
        ),
    )
    # Tasks (one per org)
    db.add(
        DatabaseTask(
            id=task1_id,
            name=f"mt-task1-{suffix}",
            created_at=now,
            updated_at=now,
            org_id=org1_id,
        ),
    )
    db.add(
        DatabaseTask(
            id=task2_id,
            name=f"mt-task2-{suffix}",
            created_at=now,
            updated_at=now,
            org_id=org2_id,
        ),
    )
    db.commit()

    # Build interleaved traces. Index i: even -> org1, odd -> org2.
    # 10 total slots, but cap org2 at 4 — slots [1, 3, 5, 7] are O2, all
    # other slots are O1 (6 traces). Earlier index = earlier start_time,
    # so DESC sort yields slot 9 (O1) first, then 8 (O1), then 7 (O2)...
    org1_trace_ids: list[str] = []
    org2_trace_ids: list[str] = []
    spans: list[DatabaseSpan] = []
    trace_metas: list[DatabaseTraceMetadata] = []
    for i in range(10):
        is_o2 = i in (1, 3, 5, 7)
        owner_org = org2_id if is_o2 else org1_id
        owner_task = task2_id if is_o2 else task1_id
        trace_id = f"mt-trace-{suffix}-{i:02d}"
        start = base_time + timedelta(seconds=i)
        end = start + timedelta(milliseconds=500)

        trace_metas.append(
            DatabaseTraceMetadata(
                trace_id=trace_id,
                task_id=owner_task,
                org_id=owner_org,
                session_id=session_id,
                user_id=f"user-{suffix}",
                span_count=1,
                start_time=start,
                end_time=end,
                created_at=start,
                updated_at=end,
            ),
        )
        spans.append(
            DatabaseSpan(
                id=uuid.uuid4().hex,
                trace_id=trace_id,
                span_id=f"mt-span-{suffix}-{i:02d}",
                parent_span_id=None,
                span_kind="LLM",
                start_time=start,
                end_time=end,
                task_id=owner_task,
                org_id=owner_org,
                session_id=session_id,
                user_id=f"user-{suffix}",
                status_code="Ok",
                raw_data={
                    "name": "mt-span",
                    "spanId": f"mt-span-{suffix}-{i:02d}",
                    "traceId": trace_id,
                    "attributes": {"openinference.span.kind": "LLM"},
                    "arthur_span_version": "arthur_span_v1",
                },
            ),
        )
        if is_o2:
            org2_trace_ids.append(trace_id)
        else:
            org1_trace_ids.append(trace_id)

    db.add_all(trace_metas)
    db.add_all(spans)
    db.commit()

    tasks_metrics_repo = TasksMetricsRepository(db)
    metrics_repo = MetricRepository(db)
    span_repo = SpanRepository(db, tasks_metrics_repo, metrics_repo)

    yield {
        "db": db,
        "session_id": session_id,
        "org1_id": org1_id,
        "org2_id": org2_id,
        "task1_id": task1_id,
        "task2_id": task2_id,
        "org1_trace_ids": org1_trace_ids,
        "org2_trace_ids": org2_trace_ids,
        "span_repo": span_repo,
    }

    # Cleanup. Order matters: spans, trace_metadata, tasks, orgs.
    span_ids = [s.span_id for s in spans]
    trace_ids = [t.trace_id for t in trace_metas]
    db.query(DatabaseSpan).filter(DatabaseSpan.span_id.in_(span_ids)).delete(
        synchronize_session=False,
    )
    db.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(trace_ids),
    ).delete(synchronize_session=False)
    db.query(DatabaseTask).filter(
        DatabaseTask.id.in_([task1_id, task2_id]),
    ).delete(synchronize_session=False)
    db.query(DatabaseOrganization).filter(
        DatabaseOrganization.id.in_([org1_id, org2_id]),
    ).delete(synchronize_session=False)
    db.commit()


@pytest.mark.unit_tests
def test_session_traces_tenant_pagination_pushes_org_filter_into_sql(
    cross_org_session,
):
    """Consolidated regression for the PR #1693 multi-tenant pagination fix.

    The fixture seeds one session_id populated by two orgs (6 O1 / 4 O2,
    interleaved start times) and is intentionally expensive (10 traces +
    10 spans + 2 orgs + 2 tasks in real DB tables), so all five
    behavioral guarantees are exercised inside this single test against
    one shared seed. Each sub-case is labeled via `case` so an assertion
    failure pinpoints which guarantee regressed.

    Sub-cases:
      1. tenant count is the org-owned total (independent of page_size)
      2. tenant reaches later pages — no 404 caused by post-filtering
      3. tenant page_size is honored — no partial slices
      4. admin (org_scope=None) sees all orgs
      5. compute_session_metrics shares the same paginate+filter contract
    """
    fx = cross_org_session
    span_repo: SpanRepository = fx["span_repo"]
    session_id = fx["session_id"]
    org1_ids = set(fx["org1_trace_ids"])
    org2_ids = set(fx["org2_trace_ids"])

    def _paginate(page, page_size, org_scope, fn=span_repo.get_session_traces):
        return fn(
            session_id=session_id,
            pagination_parameters=PaginationParameters(
                sort=PaginationSortMethod.DESCENDING,
                page=page,
                page_size=page_size,
            ),
            org_scope=org_scope,
        )

    # --- Sub-case 1: tenant count is the org-owned total -----------------
    case = "tenant count is org-owned total"
    count, traces = _paginate(page=0, page_size=10, org_scope=fx["org1_id"])
    assert count == len(fx["org1_trace_ids"]) == 6, (
        f"[{case}] count must be the O1-owned total (6), not the full "
        f"session size (10) and not a page slice. got count={count}"
    )
    returned_ids = {t.trace_id for t in traces}
    assert returned_ids == org1_ids, f"[{case}] returned ids mismatch"
    assert returned_ids.isdisjoint(org2_ids), f"[{case}] cross-org leak detected"

    # --- Sub-case 2: tenant reaches later pages (no 404) -----------------
    case = "tenant reaches later page"
    page_results = [
        _paginate(page=p, page_size=2, org_scope=fx["org1_id"]) for p in (0, 1, 2)
    ]
    page_counts = [c for c, _ in page_results]
    page_traces = [t for _, t in page_results]

    assert page_counts == [6, 6, 6], (
        f"[{case}] count must be stable across pages and equal O1-owned "
        f"total. got counts={page_counts}"
    )
    for idx, traces_on_page in enumerate(page_traces):
        assert len(traces_on_page) == 2, (
            f"[{case}] page {idx} must be fully populated (no partial "
            f"slices from post-filtering); got {len(traces_on_page)}"
        )
    seen = set().union(*({t.trace_id for t in pt} for pt in page_traces))
    assert (
        seen == org1_ids
    ), f"[{case}] union of pages must cover all O1 traces with no duplicates"
    assert seen.isdisjoint(org2_ids), f"[{case}] cross-org leak detected"

    # --- Sub-case 3: tenant page_size honored ----------------------------
    case = "tenant page_size honored"
    count, traces = _paginate(page=0, page_size=3, org_scope=fx["org1_id"])
    assert count == 6, f"[{case}] count must be O1-owned total; got {count}"
    assert (
        len(traces) == 3
    ), f"[{case}] page_size=3 must return exactly 3 items, got {len(traces)}"
    returned_ids = {t.trace_id for t in traces}
    assert returned_ids.issubset(
        org1_ids
    ), f"[{case}] all returned traces must be O1-owned"

    # --- Sub-case 4: admin sees all orgs ---------------------------------
    case = "admin sees all orgs"
    count, traces = _paginate(page=0, page_size=20, org_scope=None)
    assert count == 10, f"[{case}] admin should see all 10 traces, got {count}"
    returned_ids = {t.trace_id for t in traces}
    assert (
        returned_ids == org1_ids | org2_ids
    ), f"[{case}] admin must see union of both orgs' trace_ids"

    # --- Sub-case 5: compute_session_metrics pagination parity -----------
    case = "compute_session_metrics tenant pagination parity"
    count, traces = _paginate(
        page=0,
        page_size=10,
        org_scope=fx["org1_id"],
        fn=span_repo.compute_session_metrics,
    )
    assert count == 6, (
        f"[{case}] compute_session_metrics count must be O1-owned total; "
        f"got {count}"
    )
    returned_ids = {t.trace_id for t in traces}
    assert returned_ids == org1_ids, f"[{case}] returned ids mismatch"
    assert returned_ids.isdisjoint(org2_ids), f"[{case}] cross-org leak detected"
