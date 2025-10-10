import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple, Union

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import (
    insert as sqlite_insert,  # Unit tests are still using sqlite
)
from sqlalchemy.orm import Session

from db_models import DatabaseSpan, DatabaseTraceMetadata
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
    ) -> Tuple[list[DatabaseSpan], Tuple[int, int, int, list[str]]]:
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

                    try:
                        # Pass the resource task ID to the span processing
                        processed_span = self._process_span_data(
                            span_data,
                            resource_task_id,
                        )
                        spans_data.append(processed_span)
                        accepted_spans += 1
                    except Exception as e:
                        rejected_spans += 1
                        rejected_reasons.append("Invalid span data format.")
                        logger.debug(
                            f"Rejected span due to invalid format: \n{str(e)}",
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
    ) -> DatabaseSpan:
        """Process and clean span data, returning None if the span data is invalid."""
        span_data = self._normalize_span_attributes(span_data)
        # Inject version into raw data
        span_data[SPAN_VERSION_KEY] = EXPECTED_SPAN_VERSION
        start_time, end_time = self._extract_timestamps(span_data)

        # Extract and normalize status code
        span_status_code = span_data.get("status", {}).get("code", "Unset")
        span_status_code = trace_utils.clean_status_code(span_status_code)

        return DatabaseSpan(
            id=str(uuid.uuid4()),
            trace_id=trace_utils.convert_id_to_hex(span_data.get("traceId")),
            span_id=trace_utils.convert_id_to_hex(span_data.get("spanId")),
            parent_span_id=self._get_parent_span_id(span_data),
            span_kind=self._get_attribute_value(span_data, SPAN_KIND_KEY),
            span_name=span_data.get("name"),
            start_time=start_time,
            end_time=end_time,
            task_id=resource_task_id,
            session_id=self._get_attribute_value(span_data, "session.id"),
            status_code=span_status_code,
            raw_data=span_data,
        )

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

    def _store_spans(self, spans: list[DatabaseSpan], commit: bool = True):
        """Store spans in the database with optional commit control."""
        if not spans:
            return

        self.db_session.add_all(spans)

        # Batch trace metadata updates within this transaction
        # This avoids N separate upserts for N spans in the same trace
        self._batch_upsert_trace_metadata(spans)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans with trace metadata (commit={commit})")

    def _batch_upsert_trace_metadata(self, spans: list[DatabaseSpan]):
        """Efficiently batch trace metadata updates using native database upsert.

        Groups spans by trace_id to batch updates. For example:
        - 50 spans from same trace = 1 upsert (not 50!)
        - Handles out-of-order span arrival with MIN/MAX aggregations
        - Uses native PostgreSQL/SQLite upsert for optimal performance
        """
        if not spans:
            return

        # Group spans by trace_id to batch updates
        trace_updates = {}
        current_time = datetime.now()

        for span in spans:
            trace_id = span.trace_id
            if trace_id not in trace_updates:
                trace_updates[trace_id] = {
                    "trace_id": trace_id,
                    "task_id": span.task_id,
                    "session_id": span.session_id,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "span_count": 0,
                    "updated_at": current_time,
                }

            # Aggregate within this batch (handles multiple spans per trace in one ingestion)
            trace_updates[trace_id]["start_time"] = min(
                trace_updates[trace_id]["start_time"],
                span.start_time,
            )
            trace_updates[trace_id]["end_time"] = max(
                trace_updates[trace_id]["end_time"],
                span.end_time,
            )
            trace_updates[trace_id]["span_count"] += 1

            # Handle session_id conflicts: use first non-null session_id found
            if span.session_id and not trace_updates[trace_id]["session_id"]:
                trace_updates[trace_id]["session_id"] = span.session_id

        if not trace_updates:
            return

        # Single native upsert operation - replaces complex manual logic
        values_list = list(trace_updates.values())

        # PostgreSQL upsert with proper aggregation functions
        if self.db_session.bind.dialect.name == "postgresql":
            stmt = pg_insert(DatabaseTraceMetadata).values(values_list)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trace_id"],
                set_=dict(
                    start_time=func.least(
                        stmt.excluded.start_time,
                        DatabaseTraceMetadata.start_time,
                    ),
                    end_time=func.greatest(
                        stmt.excluded.end_time,
                        DatabaseTraceMetadata.end_time,
                    ),
                    span_count=DatabaseTraceMetadata.span_count
                    + stmt.excluded.span_count,
                    session_id=func.coalesce(
                        DatabaseTraceMetadata.session_id,
                        stmt.excluded.session_id,
                    ),
                    updated_at=stmt.excluded.updated_at,
                ),
            )

        # SQLite upsert with min/max functions
        # Needed for unit tests
        else:  # sqlite
            stmt = sqlite_insert(DatabaseTraceMetadata).values(values_list)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trace_id"],
                set_=dict(
                    start_time=func.min(
                        stmt.excluded.start_time,
                        DatabaseTraceMetadata.start_time,
                    ),
                    end_time=func.max(
                        stmt.excluded.end_time,
                        DatabaseTraceMetadata.end_time,
                    ),
                    span_count=DatabaseTraceMetadata.span_count
                    + stmt.excluded.span_count,
                    session_id=func.coalesce(
                        DatabaseTraceMetadata.session_id,
                        stmt.excluded.session_id,
                    ),
                    updated_at=stmt.excluded.updated_at,
                ),
            )

        self.db_session.execute(stmt)

        logger.debug(
            f"Upserted metadata for {len(trace_updates)} traces from {len(spans)} spans",
        )
