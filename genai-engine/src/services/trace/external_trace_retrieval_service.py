from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.cloud import trace_v1

logger = logging.getLogger(__name__)


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

    def fetch_traces_from_cloud_trace(
        self,
        task_id: str,
        project_id: str,
        reasoning_engine_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_traces: Optional[int] = None,
        timeout: float = 300.0,
    ) -> List[Dict[str, Any]]:
        """
        Fetch traces from Google Cloud Trace.

        Args:
            task_id: Task ID to associate traces with
            project_id: GCP project ID
            reasoning_engine_id: GCP Reasoning Engine ID used as Cloud Trace service.name filter
            start_time: Start time for trace query
            end_time: End time for trace query
            max_traces: Optional maximum number of traces to fetch
            timeout: Timeout in seconds for API calls

        Returns:
            List of traces in GenAI Engine format
        """

        if start_time is None or end_time is None:
            raise ValueError("start_time and end_time are required")

        logger.debug(
            f"Fetching traces from Cloud Trace for Project: {project_id} with Reasoning Engine ID: {reasoning_engine_id}",
        )

        try:
            # Initialize Cloud Trace client
            trace_client = trace_v1.TraceServiceClient()

            # List all traces filtered by reasoning engine ID
            request = trace_v1.ListTracesRequest(
                project_id=project_id,
                start_time=start_time,
                end_time=end_time,
                filter=f"+service.name:{reasoning_engine_id}",
            )

            trace_ids = []
            page_result = trace_client.list_traces(request=request, timeout=timeout)
            for trace in page_result:
                trace_ids.append(trace.trace_id)

            logger.debug(f"  Found {len(trace_ids)} total trace ID(s)")

            if max_traces:
                trace_ids = trace_ids[:max_traces]

            if not trace_ids:
                return []

            # Fetch complete traces
            traces = []
            for i, trace_id in enumerate(trace_ids, 1):
                if i % 10 == 0:
                    logger.debug(f"  Fetching trace {i}/{len(trace_ids)}...")

                get_request = trace_v1.GetTraceRequest(
                    project_id=project_id,
                    trace_id=trace_id,
                )

                try:
                    trace = trace_client.get_trace(request=get_request, timeout=timeout)
                    traces.append(trace)
                except Exception as e:
                    logger.debug(f"  Could not fetch trace {trace_id}: {e}")
                    continue

            logger.debug(f"  ✓ Fetched {len(traces)} complete trace(s)")

            # Convert traces to GenAI format
            genai_traces = []
            for i, trace in enumerate(traces, 1):
                logger.debug(f"  Sending trace {i}/{len(traces)}: {trace.trace_id}")

                genai_trace = self._convert_gcp_trace_to_genai_format(trace, task_id)
                genai_traces.append(genai_trace)

            return genai_traces

        except Exception as e:
            logger.error(f"  ✗ Failed to fetch traces: {e}")
            raise e
