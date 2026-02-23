from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from google.cloud import trace_v1

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 25


class ExternalTraceRetrievalService:
    """
    Service for fetching traces from external sources (e.g. Google Cloud Trace).
    """

    def __init__(self) -> None:
        pass

    def _convert_gcp_trace_to_genai_format(
        self,
        trace: trace_v1.Trace,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        Convert a GCP trace to the format expected by the GenAI Engine's /api/v1/traces/gcp endpoint.

        This converts the GCP Cloud Trace protobuf format to a simple JSON format with:
        - traceId, projectId at the top level
        - task_id included in the payload
        - spans array with spanId (decimal), name, timestamps, labels

        Args:
            trace: GCP Trace object from Cloud Trace API
            task_id: Task ID to associate the trace with

        Returns:
            Dictionary in GCP trace format ready for GenAI Engine ingestion
        """
        spans = []
        for span in trace.spans:
            # Build span dict in GCP format
            span_dict = {
                "spanId": str(getattr(span, "span_id", "")),  # Keep as decimal string
                "name": getattr(span, "name", ""),
                "startTime": getattr(span, "start_time", datetime.now()).isoformat(),
                "endTime": getattr(span, "end_time", datetime.now()).isoformat(),
                "labels": dict(getattr(span, "labels", {})),
            }

            # Add parent span ID if present
            parent_span_id = getattr(span, "parent_span_id", None)
            if parent_span_id:
                span_dict["parentSpanId"] = str(
                    parent_span_id,
                )  # Keep as decimal string

            spans.append(span_dict)

        # Build GCP trace structure with task_id
        gcp_trace = {
            "traceId": trace.trace_id,
            "projectId": trace.project_id,
            "task_id": task_id,  # Include task_id at top level
            "spans": spans,
        }

        return gcp_trace

    def _fetch_and_convert_page(
        self,
        trace_client: trace_v1.TraceServiceClient,
        project_id: str,
        trace_ids: List[str],
        task_id: str,
        timeout: float,
    ) -> List[Dict[str, Any]]:
        """Fetch complete traces by ID and convert them to GenAI format.

        Args:
            trace_client: Initialized GCP TraceServiceClient
            project_id: GCP project ID
            trace_ids: List of trace IDs to fetch
            task_id: Task ID to associate with traces
            timeout: Timeout for each get_trace call

        Returns:
            List of traces in GenAI Engine format
        """
        genai_traces = []

        for trace_id in trace_ids:
            get_request = trace_v1.GetTraceRequest(
                project_id=project_id,
                trace_id=trace_id,
            )
            try:
                trace = trace_client.get_trace(request=get_request, timeout=timeout)
                genai_trace = self._convert_gcp_trace_to_genai_format(trace, task_id)
                genai_traces.append(genai_trace)
            except Exception as e:
                logger.debug(f"  Could not fetch trace {trace_id}: {e}")
                continue

        logger.debug(
            f"  Fetched and converted {len(genai_traces)}/{len(trace_ids)} "
            f"trace(s) in page"
        )
        return genai_traces

    def fetch_traces_from_cloud_trace(
        self,
        task_id: str,
        project_id: str,
        reasoning_engine_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_traces: Optional[int] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        timeout: float = 300.0,
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Fetch traces from Google Cloud Trace, yielding pages of converted traces.

        Each yielded value is a list of traces (one page worth) in GenAI Engine
        format. The caller should iterate and process each page independently
        to avoid holding all traces in memory at once.

        Args:
            task_id: Task ID to associate traces with
            project_id: GCP project ID
            reasoning_engine_id: GCP Reasoning Engine ID used as Cloud Trace service.name filter
            start_time: Start time for trace query
            end_time: End time for trace query
            max_traces: Optional maximum total number of traces to fetch across all pages
            page_size: Number of traces per page (default: DEFAULT_PAGE_SIZE = 100).
                Controls both the GCP ListTracesRequest page_size and the
                internal batch size for fetching and yielding traces.
            timeout: Timeout in seconds for API calls

        Yields:
            List of traces in GenAI Engine format, one page at a time
        """

        if start_time is None or end_time is None:
            raise ValueError("start_time and end_time are required")

        logger.debug(
            f"Fetching traces from Cloud Trace for Project: {project_id} "
            f"with Reasoning Engine ID: {reasoning_engine_id}",
        )

        try:
            # Initialize Cloud Trace client
            trace_client = trace_v1.TraceServiceClient()

            # List traces filtered by reasoning engine ID
            request = trace_v1.ListTracesRequest(
                project_id=project_id,
                start_time=start_time,
                end_time=end_time,
                filter=f"+service.name:{reasoning_engine_id}",
                page_size=page_size,
            )

            page_result = trace_client.list_traces(request=request, timeout=timeout)

            total_fetched = 0
            current_page_ids: List[str] = []

            for trace in page_result:
                if max_traces and total_fetched >= max_traces:
                    break

                current_page_ids.append(trace.trace_id)
                total_fetched += 1

                # When we have a full page, fetch and yield
                if len(current_page_ids) >= page_size:
                    page_traces = self._fetch_and_convert_page(
                        trace_client=trace_client,
                        project_id=project_id,
                        trace_ids=current_page_ids,
                        task_id=task_id,
                        timeout=timeout,
                    )
                    if page_traces:
                        yield page_traces
                    current_page_ids = []

            # Yield any remaining traces in the final partial page
            if current_page_ids:
                page_traces = self._fetch_and_convert_page(
                    trace_client=trace_client,
                    project_id=project_id,
                    trace_ids=current_page_ids,
                    task_id=task_id,
                    timeout=timeout,
                )
                if page_traces:
                    yield page_traces

            logger.debug(f"  Fetched {total_fetched} total trace ID(s)")

        except Exception as e:
            logger.error(f"  ✗ Failed to fetch traces: {e}")
            raise e
