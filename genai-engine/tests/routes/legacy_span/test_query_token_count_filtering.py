import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

@pytest.mark.unit_tests
def test_trace_query_with_total_token_count_gte(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where total_token_count >= threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_gte=500,
    )
    assert status_code == 200
    assert response.count == 2
    trace_ids = {t.trace_id for t in response.traces}
    assert trace_ids == {"trace1", "trace2"}


@pytest.mark.unit_tests
def test_trace_query_with_total_token_count_lte(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where total_token_count <= threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_lte=500,
    )
    assert status_code == 200
    assert response.count == 2
    trace_ids = {t.trace_id for t in response.traces}
    assert trace_ids == {"trace1", "trace3"}


@pytest.mark.unit_tests
def test_trace_query_with_total_token_count_gt(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where total_token_count > threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_gt=500,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace2"


@pytest.mark.unit_tests
def test_trace_query_with_total_token_count_lt(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where total_token_count < threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_lt=500,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace3"


@pytest.mark.unit_tests
def test_trace_query_with_total_token_count_eq(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where total_token_count == exact value."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_eq=1500,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace2"


@pytest.mark.unit_tests
def test_trace_query_with_total_token_count_range(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces with a min/max range on total_token_count."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_gte=200,
        total_token_count_lte=600,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace1"


# ============================================================================
# PROMPT TOKEN COUNT FILTERING
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_prompt_token_count_gte(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where prompt_token_count >= threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        prompt_token_count_gte=300,
    )
    assert status_code == 200
    assert response.count == 2
    trace_ids = {t.trace_id for t in response.traces}
    assert trace_ids == {"trace1", "trace2"}


@pytest.mark.unit_tests
def test_trace_query_with_prompt_token_count_lt(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where prompt_token_count < threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        prompt_token_count_lt=100,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace3"


# ============================================================================
# COMPLETION TOKEN COUNT FILTERING
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_completion_token_count_gte(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where completion_token_count >= threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        completion_token_count_gte=200,
    )
    assert status_code == 200
    assert response.count == 2
    trace_ids = {t.trace_id for t in response.traces}
    assert trace_ids == {"trace1", "trace2"}


@pytest.mark.unit_tests
def test_trace_query_with_completion_token_count_lt(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Filter traces where completion_token_count < threshold."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        completion_token_count_lt=200,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace3"


# ============================================================================
# COMBINED TOKEN COUNT FILTERS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_multiple_token_count_types(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Combine filters across total, prompt, and completion token counts."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_gte=400,
        prompt_token_count_lte=500,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace1"


@pytest.mark.unit_tests
def test_trace_query_token_count_with_other_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Combine token count filters with span_types and duration filters."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_gte=400,
        span_types=["LLM"],
    )
    assert status_code == 200
    assert response.count == 2
    trace_ids = {t.trace_id for t in response.traces}
    assert trace_ids == {"trace1", "trace2"}

    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_lte=200,
        span_types=["LLM"],
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace3"


@pytest.mark.unit_tests
def test_trace_query_token_count_no_results(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Token count threshold that excludes all traces."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        total_token_count_gte=10000,
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


# ============================================================================
# METRICS ENDPOINT WITH TOKEN COUNT FILTERS
# ============================================================================


@pytest.mark.unit_tests
def test_traces_metrics_endpoint_with_token_count_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Verify token count filters work on the /v1/traces/metrics/ endpoint too."""
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        total_token_count_gte=1000,
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace2"

    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        total_token_count_lte=500,
    )
    assert status_code == 200
    assert response.count == 2
    trace_ids = {t.trace_id for t in response.traces}
    assert trace_ids == {"trace1", "trace3"}
