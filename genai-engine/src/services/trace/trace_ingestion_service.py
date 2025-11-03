import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple, Union

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from openinference.semconv.trace import SpanAttributes
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
from services.trace.span_normalization_service import SpanNormalizationService
from utils import trace as trace_utils
from utils.constants import (
    EXPECTED_SPAN_VERSION,
    SPAN_KIND_KEY,
    SPAN_VERSION_KEY,
    TASK_ID_KEY,
    USER_ID_KEY,
)
from utils.token_count import safe_add

logger = logging.getLogger(__name__)


class TraceIngestionService:
    """Service responsible for ingesting and processing trace data."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

        self.span_normalizer = SpanNormalizationService()

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
                        error_msg = f"Invalid span data format: {str(e)}"
                        rejected_reasons.append(error_msg)
                        logger.error(
                            f"Rejected span due to error: {str(e)}\nSpan data keys: {list(span_data.keys()) if isinstance(span_data, dict) else 'not a dict'}",
                            exc_info=True,
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

        # Extract and normalize status code (handle nested structure after normalization)
        status = span_data.get("status")
        if isinstance(status, dict):
            span_status_code = status.get("code", "Unset")
        elif isinstance(status, list) and len(status) > 0:
            # If status was converted to list (shouldn't happen but handle it)
            span_status_code = (
                status[0]
                if isinstance(status[0], (str, int))
                else (
                    status[0].get("code", "Unset")
                    if isinstance(status[0], dict)
                    else "Unset"
                )
            )
        else:
            span_status_code = (
                trace_utils.get_nested_value(span_data, "status.code") or "Unset"
            )
        span_status_code = trace_utils.clean_status_code(span_status_code)

        # Extract token/cost info (fast - from attributes only, compute cost if needed)
        span_kind = self._get_attribute_value(span_data, SPAN_KIND_KEY)
        token_data = trace_utils.extract_token_cost_from_span(span_data, span_kind)

        return DatabaseSpan(
            id=str(uuid.uuid4()),
            trace_id=trace_utils.convert_id_to_hex(span_data.get("traceId")),
            span_id=trace_utils.convert_id_to_hex(span_data.get("spanId")),
            parent_span_id=self._get_parent_span_id(span_data),
            span_kind=span_kind,
            span_name=span_data.get("name"),
            start_time=start_time,
            end_time=end_time,
            task_id=resource_task_id,
            session_id=self._get_attribute_value(span_data, SpanAttributes.SESSION_ID),
            user_id=self._get_attribute_value(span_data, USER_ID_KEY),
            status_code=span_status_code,
            raw_data=span_data,
            prompt_token_count=token_data["prompt_token_count"],
            completion_token_count=token_data["completion_token_count"],
            total_token_count=token_data["total_token_count"],
            prompt_token_cost=token_data["prompt_token_cost"],
            completion_token_cost=token_data["completion_token_cost"],
            total_token_cost=token_data["total_token_cost"],
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
        """Normalize span to nested dictionary structure with selective JSON deserialization."""
        return self.span_normalizer.normalize_span_to_nested_dict(span_data)

    def _get_attribute_value(
        self,
        span_data: dict,
        attribute_key: str,
    ) -> Optional[str]:
        """Extract a specific attribute value from nested span data."""
        attributes = span_data.get("attributes", {})

        # Navigate nested structure using dot notation
        if isinstance(attributes, dict):
            value = trace_utils.get_nested_value(attributes, attribute_key)
            return str(value) if value is not None else None

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

        TOKEN_FIELDS = [
            "prompt_token_count",
            "completion_token_count",
            "total_token_count",
            "prompt_token_cost",
            "completion_token_cost",
            "total_token_cost",
        ]

        for span in spans:
            trace_id = span.trace_id
            if trace_id not in trace_updates:

                trace_updates[trace_id] = {
                    "trace_id": trace_id,
                    "task_id": span.task_id,
                    "session_id": span.session_id,
                    "user_id": span.user_id,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "span_count": 0,
                    "updated_at": current_time,
                    "input_content": None,
                    "output_content": None,
                    "earliest_root_start_time": None,  # Track time of earliest root span
                    **{field: None for field in TOKEN_FIELDS},
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

            # Handle user_id conflicts: use first non-null user_id found
            if span.user_id and not trace_updates[trace_id]["user_id"]:
                trace_updates[trace_id]["user_id"] = span.user_id

            # Extract input/output from root spans (no parent_span_id)
            # Only use the earliest root span for each trace
            if not span.parent_span_id:
                earliest_time = trace_updates[trace_id]["earliest_root_start_time"]
                if earliest_time is None or span.start_time < earliest_time:
                    # This is the earliest root span so far, extract its input/output
                    trace_updates[trace_id][
                        "earliest_root_start_time"
                    ] = span.start_time

                    # Extract and convert to string for database storage
                    input_value = trace_utils.get_nested_value(
                        span.raw_data,
                        "attributes.input.value",
                    )
                    output_value = trace_utils.get_nested_value(
                        span.raw_data,
                        "attributes.output.value",
                    )

                    trace_updates[trace_id]["input_content"] = (
                        trace_utils.value_to_string(input_value)
                    )
                    trace_updates[trace_id]["output_content"] = (
                        trace_utils.value_to_string(output_value)
                    )

            for field in TOKEN_FIELDS:
                span_value = getattr(span, field)
                trace_updates[trace_id][field] = safe_add(
                    trace_updates[trace_id][field],
                    span_value,
                )

        if not trace_updates:
            return

        # Remove tracking field before database upsert (not a database column)
        for trace_data in trace_updates.values():
            trace_data.pop("earliest_root_start_time", None)

        # Single native upsert operation - replaces complex manual logic
        values_list = list(trace_updates.values())

        # PostgreSQL upsert with proper aggregation functions
        if self.db_session.bind.dialect.name == "postgresql":
            stmt = pg_insert(DatabaseTraceMetadata).values(values_list)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trace_id"],
                set_=self._build_upsert_set_dict(stmt, func.least, func.greatest),
            )

        # SQLite upsert with min/max functions
        # Needed for unit tests
        else:  # sqlite
            stmt = sqlite_insert(DatabaseTraceMetadata).values(values_list)
            stmt = stmt.on_conflict_do_update(
                index_elements=["trace_id"],
                set_=self._build_upsert_set_dict(stmt, func.min, func.max),
            )

        self.db_session.execute(stmt)

        logger.debug(
            f"Upserted metadata for {len(trace_updates)} traces from {len(spans)} spans",
        )

    def _build_upsert_set_dict(self, stmt, min_func, max_func) -> dict:
        """Build the set_ dictionary for upsert operations.

        Args:
            stmt: The insert statement with excluded values
            min_func: Function to use for minimum (func.least for PostgreSQL, func.min for SQLite)
            max_func: Function to use for maximum (func.greatest for PostgreSQL, func.max for SQLite)

        Returns:
            Dictionary of fields to update on conflict
        """
        return dict(
            start_time=min_func(
                stmt.excluded.start_time,
                DatabaseTraceMetadata.start_time,
            ),
            end_time=max_func(
                stmt.excluded.end_time,
                DatabaseTraceMetadata.end_time,
            ),
            span_count=DatabaseTraceMetadata.span_count + stmt.excluded.span_count,
            session_id=func.coalesce(
                DatabaseTraceMetadata.session_id,
                stmt.excluded.session_id,
            ),
            user_id=func.coalesce(
                DatabaseTraceMetadata.user_id,
                stmt.excluded.user_id,
            ),
            # NULL-safe addition: if both NULL -> NULL, if one NULL -> use non-NULL, else sum
            prompt_token_count=func.coalesce(
                DatabaseTraceMetadata.prompt_token_count
                + stmt.excluded.prompt_token_count,
                DatabaseTraceMetadata.prompt_token_count,
                stmt.excluded.prompt_token_count,
            ),
            completion_token_count=func.coalesce(
                DatabaseTraceMetadata.completion_token_count
                + stmt.excluded.completion_token_count,
                DatabaseTraceMetadata.completion_token_count,
                stmt.excluded.completion_token_count,
            ),
            total_token_count=func.coalesce(
                DatabaseTraceMetadata.total_token_count
                + stmt.excluded.total_token_count,
                DatabaseTraceMetadata.total_token_count,
                stmt.excluded.total_token_count,
            ),
            prompt_token_cost=func.coalesce(
                DatabaseTraceMetadata.prompt_token_cost
                + stmt.excluded.prompt_token_cost,
                DatabaseTraceMetadata.prompt_token_cost,
                stmt.excluded.prompt_token_cost,
            ),
            completion_token_cost=func.coalesce(
                DatabaseTraceMetadata.completion_token_cost
                + stmt.excluded.completion_token_cost,
                DatabaseTraceMetadata.completion_token_cost,
                stmt.excluded.completion_token_cost,
            ),
            total_token_cost=func.coalesce(
                DatabaseTraceMetadata.total_token_cost + stmt.excluded.total_token_cost,
                DatabaseTraceMetadata.total_token_cost,
                stmt.excluded.total_token_cost,
            ),
            # Prefer new non-null values for input/output content
            # This allows updates if a new batch provides a better root span
            input_content=func.coalesce(
                stmt.excluded.input_content,
                DatabaseTraceMetadata.input_content,
            ),
            output_content=func.coalesce(
                stmt.excluded.output_content,
                DatabaseTraceMetadata.output_content,
            ),
            updated_at=stmt.excluded.updated_at,
        )
