import logging

from schemas.enums import PaginationSortMethod
from schemas.internal_schemas import Span
from schemas.response_schemas import TraceResponse

logger = logging.getLogger(__name__)


class TreeBuildingService:
    """Service responsible for building trace tree structures from spans."""

    def group_spans_into_traces(
        self,
        spans: list[Span],
        sort: PaginationSortMethod,
    ) -> list:
        """Group spans into a nested trace structure."""
        if not spans:
            return []

        # Group spans by trace_id
        traces_dict = {}
        for span in spans:
            trace_id = span.trace_id
            if trace_id not in traces_dict:
                traces_dict[trace_id] = []
            traces_dict[trace_id].append(span)

        # Build trace responses
        traces = []
        for trace_id, trace_spans in traces_dict.items():
            # Calculate trace start and end times
            start_time = min(span.start_time for span in trace_spans)
            end_time = max(span.end_time for span in trace_spans)

            # Build nested spans for this trace
            root_spans = self._build_span_tree(trace_spans)

            trace_response = TraceResponse(
                trace_id=trace_id,
                start_time=start_time,
                end_time=end_time,
                root_spans=root_spans,
            )
            traces.append(trace_response)

        if sort == PaginationSortMethod.ASCENDING:
            traces.sort(key=lambda t: t.start_time, reverse=False)
        else:
            traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces

    def _build_span_tree(self, spans: list[Span]) -> list:
        """Build a nested tree structure from a list of spans."""
        if not spans:
            return []

        # Create a mapping to store children for each span
        children_by_parent = {}
        root_spans = []

        # First pass: identify parent-child relationships
        for span in spans:
            parent_id = span.parent_span_id
            if parent_id is None:
                # This is a root span
                root_spans.append(span)
            else:
                # This span has a parent
                if parent_id not in children_by_parent:
                    children_by_parent[parent_id] = []
                children_by_parent[parent_id].append(span)

        # Second pass: build nested structure recursively
        def build_nested_span(span: Span):
            # Get children for this span (if any)
            children_spans = children_by_parent.get(span.span_id, [])
            children_spans.sort(key=lambda s: s.start_time)
            # Recursively build nested children
            nested_children = [build_nested_span(child) for child in children_spans]

            return span._to_nested_metrics_response_model(children=nested_children)

        # Sort root spans by start_time (ascending)
        root_spans.sort(key=lambda s: s.start_time)
        return [build_nested_span(root_span) for root_span in root_spans]
