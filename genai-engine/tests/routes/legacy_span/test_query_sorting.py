"""Tests for server-side sorting of trace queries via the sort_by parameter."""

import pytest


@pytest.mark.unit_tests
def test_sort_by_total_token_count_ascending(client, create_test_spans):
    """Sort by total_token_count ascending: trace3 (100) < trace1 (500) < trace2 (1500)."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="asc",
        sort_by="total_token_count",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace3", "trace1", "trace2"]


@pytest.mark.unit_tests
def test_sort_by_total_token_count_descending(client, create_test_spans):
    """Sort by total_token_count descending: trace2 (1500) > trace1 (500) > trace3 (100)."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
        sort_by="total_token_count",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace2", "trace1", "trace3"]


@pytest.mark.unit_tests
def test_sort_by_total_token_cost_ascending(client, create_test_spans):
    """Sort by total_token_cost ascending: trace3 (0.01) < trace1 (0.05) < trace2 (0.15)."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="asc",
        sort_by="total_token_cost",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace3", "trace1", "trace2"]


@pytest.mark.unit_tests
def test_sort_by_total_token_cost_descending(client, create_test_spans):
    """Sort by total_token_cost descending: trace2 (0.15) > trace1 (0.05) > trace3 (0.01)."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
        sort_by="total_token_cost",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace2", "trace1", "trace3"]


@pytest.mark.unit_tests
def test_sort_by_span_count_ascending(client, create_test_spans):
    """All test traces have span_count=2, so order is stable but all returned."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="asc",
        sort_by="span_count",
    )
    assert status_code == 200
    assert len(response.traces) == 3


@pytest.mark.unit_tests
def test_sort_by_span_count_descending(client, create_test_spans):
    """All test traces have span_count=2, so order is stable but all returned."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
        sort_by="span_count",
    )
    assert status_code == 200
    assert len(response.traces) == 3


@pytest.mark.unit_tests
def test_sort_by_start_time_ascending(client, create_test_spans):
    """Default sort column. trace1 is oldest, trace2 is next, trace3 is newest."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="asc",
        sort_by="start_time",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace1", "trace2", "trace3"]


@pytest.mark.unit_tests
def test_sort_by_start_time_descending(client, create_test_spans):
    """Default sort column descending. trace3 is newest, trace2 is next, trace1 is oldest."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
        sort_by="start_time",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace3", "trace2", "trace1"]


@pytest.mark.unit_tests
def test_default_sort_is_start_time_descending(client, create_test_spans):
    """When no sort_by is provided, default sort is start_time descending."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace3", "trace2", "trace1"]


@pytest.mark.unit_tests
def test_sort_by_total_token_count_with_metrics_endpoint(client, create_test_spans):
    """sort_by works on the /traces/metrics/ endpoint too."""
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="asc",
        sort_by="total_token_count",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace3", "trace1", "trace2"]


@pytest.mark.unit_tests
def test_sort_by_with_filtering_combined(client, create_test_spans):
    """sort_by works combined with token count filtering."""
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
        sort_by="total_token_count",
        total_token_count_gte=100,
        total_token_count_lte=1500,
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace2", "trace1", "trace3"]


@pytest.mark.unit_tests
def test_sort_by_with_task_filter(client, create_test_spans):
    """sort_by works when filtering to a single task."""
    status_code, response = client.query_traces(
        task_ids=["task1"],
        sort="asc",
        sort_by="total_token_count",
    )
    assert status_code == 200
    trace_ids = [t.trace_id for t in response.traces]
    assert trace_ids == ["trace3", "trace1"]
