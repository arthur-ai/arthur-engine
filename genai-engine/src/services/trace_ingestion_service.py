import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple, Union

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from db_models.db_models import DatabaseSpan, DatabaseTraceMetadata
from utils import trace as trace_utils
from utils.constants import (
    EXPECTED_SPAN_VERSION,
    SPAN_KIND_KEY,
    SPAN_VERSION_KEY,
    TASK_ID_KEY,
)

logger = logging.getLogger(__name__)


class TraceIngestionService:
    """Service responsible for ingesting and processing trace data."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def process_trace_data(self, trace_data: bytes) -> Tuple[int, int, int, list[str]]:
        """Process trace data from protobuf format and return statistics."""
        json_traces = self._grpc_trace_to_dict(trace_data)
        spans_data, stats = self._extract_and_process_spans(json_traces)

        if spans_data:
            self._store_spans(spans_data, commit=True)
            logger.debug(f"Stored {len(spans_data)} spans successfully")

        return stats

    def _grpc_trace_to_dict(self, trace_data: bytes) -> dict:
        """Convert gRPC trace data to dictionary format."""
        try:
            trace_request = ExportTraceServiceRequest()
            trace_request.ParseFromString(trace_data)
            return MessageToDict(trace_request)
        except DecodeError as e:
            raise DecodeError("Failed to decode protobuf message.") from e

    def _extract_and_process_spans(
        self,
        json_traces: dict,
    ) -> Tuple[list[dict], Tuple[int, int, int, list[str]]]:
        """Extract and process spans from JSON trace data."""
        total_spans = 0
        accepted_spans = 0
        rejected_spans = 0
        rejected_reasons = []
        spans_data = []

        for resource_span in json_traces.get("resourceSpans", []):
            # Extract task ID from resource attributes (new format)
            resource_task_id = self._extract_task_id_from_resource_attributes(
                resource_span,
            )

            # Validate task ID at resource level - reject entire resource if invalid
            if not self._is_valid_task_id(resource_task_id):
                # Count all spans in this resource as rejected
                resource_span_count = sum(
                    len(scope_span.get("spans", []))
                    for scope_span in resource_span.get("scopeSpans", [])
                )
                total_spans += resource_span_count
                rejected_spans += resource_span_count
                rejected_reasons.extend(
                    ["Missing or invalid task ID in resource attributes"]
                    * resource_span_count,
                )

                logger.warning(
                    f"Rejecting entire resource with {resource_span_count} spans - "
                    f"no valid task ID found in resource attributes (task_id: {resource_task_id})",
                )
                continue  # Skip processing all spans in this resource

            logger.debug(f"Found valid resource task ID: {resource_task_id}")

            for scope_span in resource_span.get("scopeSpans", []):
                for span_data in scope_span.get("spans", []):
                    total_spans += 1
                    # Pass the resource task ID to the span processing
                    processed_span = self._process_span_data(
                        span_data,
                        resource_task_id,
                    )

                    if processed_span:
                        processed_span["id"] = str(uuid.uuid4())
                        spans_data.append(processed_span)
                        accepted_spans += 1
                    else:
                        rejected_spans += 1
                        rejected_reasons.append("Invalid span data format.")
                        logger.debug(
                            f"Rejected span due to invalid format: \n{span_data}",
                        )

        return spans_data, (
            total_spans,
            accepted_spans,
            rejected_spans,
            rejected_reasons,
        )

    def _extract_task_id_from_resource_attributes(
        self,
        resource_span: dict,
    ) -> Optional[str]:
        """
        Extract task ID from resource attributes.

        Args:
            resource_span: Dictionary containing resource span data

        Returns:
            Task ID string if found, None otherwise
        """
        attributes = resource_span.get("resource", {}).get("attributes", [])

        for attr in attributes:
            if isinstance(attr, dict) and attr.get("key") == TASK_ID_KEY:
                value = self._extract_value_from_otel_format(attr.get("value", {}))
                return str(value) if value is not None else None
        return None

    def _process_span_data(
        self,
        span_data: dict,
        resource_task_id: str,
    ) -> Optional[dict]:
        """Process and clean span data, returning None if the span data is invalid."""
        normalized_span_data = self._normalize_span_attributes(span_data)

        # Extract basic span information
        span_dict = self._extract_basic_span_info(normalized_span_data)

        # Task ID is already validated at resource level, so we can use it directly
        span_dict["task_id"] = resource_task_id

        # Inject version into raw data
        normalized_span_data[SPAN_VERSION_KEY] = EXPECTED_SPAN_VERSION

        # Store the normalized span data
        span_dict["raw_data"] = normalized_span_data

        return span_dict

    def _extract_basic_span_info(self, span_data: dict) -> dict:
        """Extract basic span information from normalized span data."""
        span_dict = {
            "trace_id": trace_utils.convert_id_to_hex(span_data.get("traceId")),
            "span_id": trace_utils.convert_id_to_hex(span_data.get("spanId")),
        }

        # Extract span name from OpenTelemetry 'name' field
        span_name = span_data.get("name")
        if span_name:
            span_dict["span_name"] = span_name[:255]  # Truncate to column limit

        # Extract parent span ID
        parent_span_id = self._get_parent_span_id(span_data)
        if parent_span_id:
            span_dict["parent_span_id"] = parent_span_id

        # Extract span kind
        span_kind = self._get_attribute_value(span_data, SPAN_KIND_KEY)
        if span_kind:
            span_dict["span_kind"] = span_kind

        # Extract timestamps
        start_time, end_time = self._extract_timestamps(span_data)
        span_dict["start_time"] = start_time
        span_dict["end_time"] = end_time

        return span_dict

    def _extract_value_from_otel_format(
        self,
        value_dict: dict,
    ) -> Optional[Union[str, int, float, bool]]:
        """
        Extract value from OpenTelemetry value format, preserving original types.

        Args:
            value_dict: OpenTelemetry value dictionary

        Returns:
            Value in its native Python type, or None if not found
        """
        if not isinstance(value_dict, dict):
            return None

        # Handle different OpenTelemetry value types
        if "stringValue" in value_dict:
            return value_dict["stringValue"]
        elif "intValue" in value_dict:
            return value_dict["intValue"]
        elif "doubleValue" in value_dict:
            return value_dict["doubleValue"]
        elif "boolValue" in value_dict:
            return value_dict["boolValue"]

        return None

    def _is_valid_task_id(self, task_id: str) -> bool:
        """Validate that a task ID is a non-empty string."""
        return isinstance(task_id, str) and bool(task_id.strip())

    def _normalize_span_attributes(self, span_data: dict) -> dict:
        """Normalize span attributes from OpenTelemetry format to flat key-value pairs."""
        normalized_span = span_data.copy()

        if "attributes" in normalized_span:
            normalized_attributes = trace_utils.extract_attributes_from_raw_data(
                normalized_span,
            )
            normalized_span["attributes"] = normalized_attributes

        return normalized_span

    def _get_attribute_value(
        self,
        span_data: dict,
        attribute_key: str,
    ) -> Optional[str]:
        """Extract a specific attribute value from span data."""
        attributes = span_data.get("attributes", {})

        # Attributes should already be normalized (flat dict)
        if isinstance(attributes, dict):
            return attributes.get(attribute_key)

        # Fallback for backward compatibility with OpenTelemetry format
        if isinstance(attributes, list):
            for attr in attributes:
                key = attr.get("key")
                value = attr.get("value", {})
                if key == attribute_key:
                    return value.get("stringValue")

        return None

    def _get_parent_span_id(self, span_data: dict) -> Optional[str]:
        """Extract parent span ID from span data."""
        if "parentSpanId" in span_data:
            return trace_utils.convert_id_to_hex(span_data.get("parentSpanId"))
        return None

    def _extract_timestamps(
        self,
        span_data: dict,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract and convert timestamps from span data."""
        start_time = None
        end_time = None

        if "startTimeUnixNano" in span_data:
            start_time_ns = int(span_data.get("startTimeUnixNano", 0))
            start_time = trace_utils.timestamp_ns_to_datetime(start_time_ns)

        if "endTimeUnixNano" in span_data:
            end_time_ns = int(span_data.get("endTimeUnixNano", 0))
            end_time = trace_utils.timestamp_ns_to_datetime(end_time_ns)

        return start_time, end_time

    def _store_spans(self, spans: list[dict], commit: bool = True):
        """Enhanced to maintain trace metadata with efficient batching.

        This method stores spans and efficiently batches trace metadata updates
        within the same transaction, preventing N upserts for N spans in the same trace.
        """
        if not spans:
            return

        # Store spans immediately
        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)

        # Batch trace metadata updates within this transaction
        # This avoids N separate upserts for N spans in the same trace
        self._batch_upsert_trace_metadata(spans)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans with trace metadata (commit={commit})")

    def _batch_upsert_trace_metadata(self, spans: list[dict]):
        """Efficiently batch trace metadata updates - prevents N upserts for N spans.

        Groups spans by trace_id to batch updates. For example:
        - 50 spans from same trace = 1 upsert (not 50!)
        - Handles out-of-order span arrival with MIN/MAX aggregations
        - Maintains data consistency within single transaction
        - Database-agnostic implementation using insert-or-update pattern
        """
        if not spans:
            return

        # Group spans by trace_id to batch updates
        trace_updates = {}
        current_time = datetime.now()

        for span in spans:
            trace_id = span["trace_id"]
            if trace_id not in trace_updates:
                trace_updates[trace_id] = {
                    "trace_id": trace_id,
                    "task_id": span["task_id"],
                    "start_time": span["start_time"],
                    "end_time": span["end_time"],
                    "span_count": 0,
                }

            # Aggregate within this batch (handles multiple spans per trace in one ingestion)
            trace_updates[trace_id]["start_time"] = min(
                trace_updates[trace_id]["start_time"],
                span["start_time"],
            )
            trace_updates[trace_id]["end_time"] = max(
                trace_updates[trace_id]["end_time"],
                span["end_time"],
            )
            trace_updates[trace_id]["span_count"] += 1

        if not trace_updates:
            return

        # Database-agnostic upsert: check existing records and separate inserts from updates
        trace_ids = list(trace_updates.keys())
        existing_traces = (
            self.db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id.in_(trace_ids),
                ),
            )
            .scalars()
            .all()
        )

        existing_trace_ids = {trace.trace_id for trace in existing_traces}

        # Prepare records for insertion (new traces)
        new_traces = []
        for trace_id, trace_data in trace_updates.items():
            if trace_id not in existing_trace_ids:
                trace_data["updated_at"] = current_time
                new_traces.append(trace_data)

        # Batch insert new traces
        if new_traces:
            self.db_session.execute(insert(DatabaseTraceMetadata).values(new_traces))

        # Update existing traces with proper aggregation
        for existing_trace in existing_traces:
            trace_id = existing_trace.trace_id
            new_data = trace_updates[trace_id]

            update_stmt = (
                update(DatabaseTraceMetadata)
                .where(DatabaseTraceMetadata.trace_id == trace_id)
                .values(
                    start_time=func.least(
                        existing_trace.start_time,
                        new_data["start_time"],
                    ),
                    end_time=func.greatest(
                        existing_trace.end_time,
                        new_data["end_time"],
                    ),
                    span_count=existing_trace.span_count + new_data["span_count"],
                    updated_at=current_time,
                )
            )
            self.db_session.execute(update_stmt)

        logger.debug(
            f"Updated metadata for {len(trace_updates)} traces from {len(spans)} spans "
            f"({len(new_traces)} new, {len(existing_traces)} updated)",
        )
