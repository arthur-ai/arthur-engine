"""Unit tests for ExternalTraceRetrievalService."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from services.trace.external_trace_retrieval_service import (
    DEFAULT_PAGE_SIZE,
    ExternalTraceRetrievalService,
)


def _make_mock_trace(trace_id: str, project_id: str = "test-project"):
    """Create a mock GCP Trace object."""
    trace = MagicMock()
    trace.trace_id = trace_id
    trace.project_id = project_id
    trace.spans = []
    return trace


def _make_mock_list_entry(trace_id: str):
    """Create a mock list_traces entry (only has trace_id)."""
    entry = MagicMock()
    entry.trace_id = trace_id
    return entry


@pytest.mark.unit_tests
def test_missing_start_time_raises():
    service = ExternalTraceRetrievalService()
    with pytest.raises(ValueError, match="start_time and end_time are required"):
        list(
            service.fetch_traces_from_cloud_trace(
                task_id="t1",
                project_id="p1",
                reasoning_engine_id="re1",
                start_time=None,
                end_time=datetime.now(),
            )
        )


@pytest.mark.unit_tests
def test_missing_end_time_raises():
    service = ExternalTraceRetrievalService()
    with pytest.raises(ValueError, match="start_time and end_time are required"):
        list(
            service.fetch_traces_from_cloud_trace(
                task_id="t1",
                project_id="p1",
                reasoning_engine_id="re1",
                start_time=datetime.now(),
                end_time=None,
            )
        )


@pytest.mark.unit_tests
@patch("services.trace.external_trace_retrieval_service.trace_v1")
def test_empty_results_yields_nothing(mock_trace_v1):
    """When no traces match the filter, the generator yields nothing."""
    mock_client = MagicMock()
    mock_trace_v1.TraceServiceClient.return_value = mock_client
    mock_client.list_traces.return_value = iter([])

    service = ExternalTraceRetrievalService()
    now = datetime.now()
    pages = list(
        service.fetch_traces_from_cloud_trace(
            task_id="t1",
            project_id="test-project",
            reasoning_engine_id="re1",
            start_time=now - timedelta(days=1),
            end_time=now,
        )
    )

    assert pages == []


@pytest.mark.unit_tests
@patch("services.trace.external_trace_retrieval_service.trace_v1")
def test_single_page_yield(mock_trace_v1):
    """When traces fit in one page, yields exactly one list."""
    mock_client = MagicMock()
    mock_trace_v1.TraceServiceClient.return_value = mock_client

    # 3 traces, page_size=10 => all in one page
    list_entries = [_make_mock_list_entry(f"trace-{i}") for i in range(3)]
    mock_client.list_traces.return_value = iter(list_entries)

    full_traces = {
        f"trace-{i}": _make_mock_trace(f"trace-{i}") for i in range(3)
    }

    def mock_get_trace(request, timeout):
        return full_traces[request.trace_id]

    mock_trace_v1.GetTraceRequest = lambda **kwargs: MagicMock(**kwargs)
    mock_client.get_trace.side_effect = mock_get_trace

    service = ExternalTraceRetrievalService()
    now = datetime.now()
    pages = list(
        service.fetch_traces_from_cloud_trace(
            task_id="t1",
            project_id="test-project",
            reasoning_engine_id="re1",
            start_time=now - timedelta(days=1),
            end_time=now,
            page_size=10,
        )
    )

    assert len(pages) == 1
    assert len(pages[0]) == 3
    assert pages[0][0]["traceId"] == "trace-0"
    assert pages[0][0]["task_id"] == "t1"


@pytest.mark.unit_tests
@patch("services.trace.external_trace_retrieval_service.trace_v1")
def test_multiple_pages_yield(mock_trace_v1):
    """When traces exceed page_size, yields multiple pages."""
    mock_client = MagicMock()
    mock_trace_v1.TraceServiceClient.return_value = mock_client

    # 5 traces, page_size=2 => 2 full pages + 1 partial page
    list_entries = [_make_mock_list_entry(f"trace-{i}") for i in range(5)]
    mock_client.list_traces.return_value = iter(list_entries)

    full_traces = {
        f"trace-{i}": _make_mock_trace(f"trace-{i}") for i in range(5)
    }

    def mock_get_trace(request, timeout):
        return full_traces[request.trace_id]

    mock_trace_v1.GetTraceRequest = lambda **kwargs: MagicMock(**kwargs)
    mock_client.get_trace.side_effect = mock_get_trace

    service = ExternalTraceRetrievalService()
    now = datetime.now()
    pages = list(
        service.fetch_traces_from_cloud_trace(
            task_id="t1",
            project_id="test-project",
            reasoning_engine_id="re1",
            start_time=now - timedelta(days=1),
            end_time=now,
            page_size=2,
        )
    )

    assert len(pages) == 3
    assert len(pages[0]) == 2  # First full page
    assert len(pages[1]) == 2  # Second full page
    assert len(pages[2]) == 1  # Final partial page


@pytest.mark.unit_tests
@patch("services.trace.external_trace_retrieval_service.trace_v1")
def test_max_traces_caps_total(mock_trace_v1):
    """max_traces stops iteration before exhausting all results."""
    mock_client = MagicMock()
    mock_trace_v1.TraceServiceClient.return_value = mock_client

    # 10 traces available, but max_traces=3, page_size=2
    list_entries = [_make_mock_list_entry(f"trace-{i}") for i in range(10)]
    mock_client.list_traces.return_value = iter(list_entries)

    full_traces = {
        f"trace-{i}": _make_mock_trace(f"trace-{i}") for i in range(10)
    }

    def mock_get_trace(request, timeout):
        return full_traces[request.trace_id]

    mock_trace_v1.GetTraceRequest = lambda **kwargs: MagicMock(**kwargs)
    mock_client.get_trace.side_effect = mock_get_trace

    service = ExternalTraceRetrievalService()
    now = datetime.now()
    pages = list(
        service.fetch_traces_from_cloud_trace(
            task_id="t1",
            project_id="test-project",
            reasoning_engine_id="re1",
            start_time=now - timedelta(days=1),
            end_time=now,
            max_traces=3,
            page_size=2,
        )
    )

    total_traces = sum(len(p) for p in pages)
    assert total_traces == 3


@pytest.mark.unit_tests
@patch("services.trace.external_trace_retrieval_service.trace_v1")
def test_get_trace_failure_skips_individual_trace(mock_trace_v1):
    """If get_trace fails for one ID, it is skipped but others succeed."""
    mock_client = MagicMock()
    mock_trace_v1.TraceServiceClient.return_value = mock_client

    list_entries = [_make_mock_list_entry(f"trace-{i}") for i in range(3)]
    mock_client.list_traces.return_value = iter(list_entries)

    good_trace = _make_mock_trace("trace-0")
    good_trace_2 = _make_mock_trace("trace-2")

    call_count = 0

    def mock_get_trace(request, timeout):
        nonlocal call_count
        call_count += 1
        if request.trace_id == "trace-1":
            raise Exception("API error for trace-1")
        if request.trace_id == "trace-0":
            return good_trace
        return good_trace_2

    mock_trace_v1.GetTraceRequest = lambda **kwargs: MagicMock(**kwargs)
    mock_client.get_trace.side_effect = mock_get_trace

    service = ExternalTraceRetrievalService()
    now = datetime.now()
    pages = list(
        service.fetch_traces_from_cloud_trace(
            task_id="t1",
            project_id="test-project",
            reasoning_engine_id="re1",
            start_time=now - timedelta(days=1),
            end_time=now,
            page_size=10,
        )
    )

    # One page with 2 successful traces (trace-1 was skipped)
    assert len(pages) == 1
    assert len(pages[0]) == 2


@pytest.mark.unit_tests
@patch("services.trace.external_trace_retrieval_service.trace_v1")
def test_page_size_passed_to_list_traces_request(mock_trace_v1):
    """Verify page_size is forwarded to the GCP ListTracesRequest."""
    mock_client = MagicMock()
    mock_trace_v1.TraceServiceClient.return_value = mock_client
    mock_client.list_traces.return_value = iter([])

    service = ExternalTraceRetrievalService()
    now = datetime.now()
    list(
        service.fetch_traces_from_cloud_trace(
            task_id="t1",
            project_id="test-project",
            reasoning_engine_id="re1",
            start_time=now - timedelta(days=1),
            end_time=now,
            page_size=50,
        )
    )

    mock_trace_v1.ListTracesRequest.assert_called_once()
    call_kwargs = mock_trace_v1.ListTracesRequest.call_args.kwargs
    assert call_kwargs["page_size"] == 50


@pytest.mark.unit_tests
def test_convert_gcp_trace_to_genai_format():
    """Test the GCP trace to GenAI format conversion."""
    mock_span = MagicMock()
    mock_span.span_id = 12345
    mock_span.name = "test-span"
    mock_span.start_time = datetime(2026, 1, 1, 0, 0, 0)
    mock_span.end_time = datetime(2026, 1, 1, 0, 0, 1)
    mock_span.labels = {"key": "value"}
    mock_span.parent_span_id = 99999

    mock_trace = MagicMock()
    mock_trace.trace_id = "abc123"
    mock_trace.project_id = "test-project"
    mock_trace.spans = [mock_span]

    service = ExternalTraceRetrievalService()
    result = service._convert_gcp_trace_to_genai_format(mock_trace, "task-1")

    assert result["traceId"] == "abc123"
    assert result["projectId"] == "test-project"
    assert result["task_id"] == "task-1"
    assert len(result["spans"]) == 1
    assert result["spans"][0]["spanId"] == "12345"
    assert result["spans"][0]["name"] == "test-span"
    assert result["spans"][0]["parentSpanId"] == "99999"
    assert result["spans"][0]["labels"] == {"key": "value"}
