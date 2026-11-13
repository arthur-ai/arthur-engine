import logging
import uuid
from datetime import datetime
from typing import Any, Callable, Optional, TypedDict, cast

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from openinference.semconv.trace import SpanAttributes
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.dialects.postgresql import Insert as PGInsertType
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import Insert as SQLiteInsertType
from sqlalchemy.dialects.sqlite import (
    insert as sqlite_insert,  # Unit tests are still using sqlite
)
from sqlalchemy.orm import InstrumentedAttribute, Session

from db_models import DatabaseSpan, DatabaseTask, DatabaseTraceMetadata
from dependencies import get_task_repository
from repositories.configuration_repository import ConfigurationRepository
from repositories.organizations_repository import lookup_org_id
from repositories.resource_metadata_repository import ResourceMetadataRepository
from repositories.service_name_mapping_repository import (
    ServiceNameMappingRepository,
)
from services.trace.span_normalization_service import SpanNormalizationService
from utils import trace as trace_utils
from utils.constants import (
    DEFAULT_ORG_ID,
    EXPECTED_SPAN_VERSION,
    SERVICE_NAME_KEY,
    SPAN_KIND_KEY,
    SPAN_VERSION_KEY,
    TASK_ID_KEY,
    UNMAPPED_TASK_ID,
    USER_ID_KEY,
)
from utils.gcp import parse_gcp_resource_path
from utils.token_count import safe_add

logger = logging.getLogger(__name__)


class TraceUpdateDBBase(TypedDict):
    """Base dictionary structure for trace metadata updates during ingestion."""

    trace_id: str
    task_id: str
    org_id: uuid.UUID
    root_span_resource_id: str | None
    session_id: str | None
    user_id: str | None
    start_time: datetime
    end_time: datetime
    span_count: int | None
    updated_at: datetime

    prompt_token_count: int | float | None
    completion_token_count: int | float | None
    total_token_count: int | float | None
    prompt_token_cost: float | None
    completion_token_cost: float | None
    total_token_cost: float | None
    ingest_bytes: int | None
    input_content: str | None
    output_content: str | None


class TraceUpdateDict(TraceUpdateDBBase):
    """Dictionary structure for trace metadata updates during ingestion."""

    earliest_root_start_time: datetime | None


class TraceIngestionService:
    """Service responsible for ingesting and processing trace data."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.span_normalizer = SpanNormalizationService()

        config_repo = ConfigurationRepository(db_session)
        app_config = config_repo.get_configurations()
        self.task_repo = get_task_repository(db_session, app_config)

    def process_trace_data(
        self,
        trace_data: bytes,
        commit: bool = True,
        count_ingest_bytes: bool = False,
        task_scope: Optional[str] = None,
    ) -> tuple[list[DatabaseSpan], tuple[int, int, int, list[str]]]:
        """Process trace data from protobuf format and return statistics.

        With task_scope (the caller's key is scoped to one task), every span lands
        in that task: a resource with no arthur.task attribute goes to it, and a
        resource naming any other task is rejected. Service-name mapping and task
        auto-creation are skipped.

        With count_ingest_bytes, each span records its share of len(trace_data), the
        request body as received, and the shares add up to it exactly unless every
        span of some trace in a resource span is rejected. Only the trace ingestion endpoints
        set it: the bytes are customer ingest volume.
        """
        trace_request = self._parse_trace_request(trace_data)
        json_traces = cast(dict[str, Any], MessageToDict(trace_request))
        span_ingest_bytes = (
            self._span_ingest_bytes(trace_request, len(trace_data))
            if count_ingest_bytes
            else None
        )

        spans_data, stats = self._extract_and_process_spans(
            json_traces,
            span_ingest_bytes,
            task_scope,
        )

        if spans_data:
            self._store_spans(spans_data, commit=commit)
            logger.debug(f"Stored {len(spans_data)} spans successfully")

        return spans_data, stats

    @staticmethod
    def _parse_trace_request(trace_data: bytes) -> ExportTraceServiceRequest:
        try:
            trace_request = ExportTraceServiceRequest()
            trace_request.ParseFromString(trace_data)
            return trace_request
        except DecodeError as e:
            raise DecodeError("Failed to decode protobuf message.") from e

    @staticmethod
    def _span_ingest_bytes(
        trace_request: ExportTraceServiceRequest,
        body_size: int,
    ) -> list[int]:
        """Split the request body's size across its spans, in span order.

        Each span is weighted by its own encoded size plus an even share of its
        resource's overhead (resource attributes, scopes), so the bytes for one
        request can be attributed to the traces and tasks it carried. Largest
        remainder rounding makes the shares sum to body_size exactly.
        """
        weights: list[float] = []
        for resource_span in trace_request.resource_spans:
            span_sizes = [
                span.ByteSize()
                for scope_span in resource_span.scope_spans
                for span in scope_span.spans
            ]
            if not span_sizes:
                continue
            overhead = max(resource_span.ByteSize() - sum(span_sizes), 0)
            weights.extend(size + overhead / len(span_sizes) for size in span_sizes)

        return TraceIngestionService._split_by_weight(body_size, weights)

    @staticmethod
    def _split_by_weight(total: int, weights: list[float]) -> list[int]:
        """Split total proportionally to weights (evenly if they are all zero).
        Largest remainder rounding makes the shares sum to total exactly."""
        if not weights:
            return []
        total_weight = sum(weights)
        if total_weight <= 0:
            weights = [1.0] * len(weights)
            total_weight = float(len(weights))

        exact = [total * weight / total_weight for weight in weights]
        shares = [int(value) for value in exact]
        by_remainder = sorted(
            range(len(exact)),
            key=lambda i: exact[i] - shares[i],
            reverse=True,
        )
        for i in by_remainder[: total - sum(shares)]:
            shares[i] += 1
        return shares

    def _extract_and_process_spans(
        self,
        json_traces: dict[str, Any],
        span_ingest_bytes: list[int] | None = None,
        task_scope: Optional[str] = None,
    ) -> tuple[list[DatabaseSpan], tuple[int, int, int, list[str]]]:
        """Extract and process spans from JSON trace data.

        span_ingest_bytes, when given, holds each span's ingest bytes in the order
        the spans appear in the request (MessageToDict keeps that order).
        """
        total_spans = 0
        accepted_spans = 0
        rejected_spans = 0
        rejected_reasons = []
        spans_data: list[DatabaseSpan] = []

        for resource_span in json_traces.get("resourceSpans", []):
            # Extract task ID from resource attributes (new format)
            resource_task_id = self._extract_task_id_from_resource_attributes(
                resource_span,
            )

            if (
                task_scope is not None
                and resource_task_id is not None
                and resource_task_id != task_scope
            ):
                # Count every span in the rejected resource so the span indexes
                # into span_ingest_bytes stay aligned for the resources after it.
                span_count = sum(
                    len(scope_span.get("spans", []))
                    for scope_span in resource_span.get("scopeSpans", [])
                )
                total_spans += span_count
                rejected_spans += span_count
                rejected_reasons.append(
                    f"Rejected {span_count} spans for task {resource_task_id}: "
                    "this API key is scoped to a different task.",
                )
                continue

            # Extract all resource attributes
            resource_attributes = self._extract_all_resource_attributes(resource_span)
            service_name = resource_attributes.get(SERVICE_NAME_KEY)

            # Create or retrieve resource metadata record
            resource_id = None
            if resource_attributes:
                try:
                    resource_id = self._create_or_get_resource_metadata(
                        resource_attributes,
                        service_name,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to create resource metadata: {e}",
                        exc_info=True,
                    )

            # Resolve task_id using priority hierarchy
            # This ensures all traces have a task_id (no NULL values)
            resolved_task_id = (
                task_scope
                if task_scope is not None
                else self._resolve_task_id(
                    explicit_task_id=resource_task_id,
                    service_name=service_name,
                    resource_attributes=resource_attributes,
                )
            )

            logger.debug(f"Resolved task_id: {resolved_task_id}")

            # Resolve the org_id for this batch from the owning task. Cheaper
            # than threading the task-org join through every read, but the
            # task→org binding can't change without a re-ingest so caching
            # per resource_span is safe. Fall back to DEFAULT_ORG_ID if the
            # task disappeared between resolve and lookup (shouldn't happen
            # since `_resolve_task_id` guarantees the row exists or auto-creates).
            resolved_org_id = lookup_org_id(
                self.db_session,
                select(DatabaseTask.org_id).where(DatabaseTask.id == resolved_task_id),
                default=DEFAULT_ORG_ID,
            )

            # A scoped key may not add spans to a trace another task already owns:
            # trace metadata keeps its first task, so the spans would surface there.
            foreign_traces = (
                self._traces_owned_by_other_tasks(resource_span, task_scope)
                if task_scope is not None
                else set()
            )

            # Per trace in this resource span, keyed by the span's raw traceId:
            # bytes received, stored spans, and whether any span was rejected.
            trace_bytes: dict[Any, int] = {}
            trace_stored: dict[Any, list[DatabaseSpan]] = {}
            traces_with_rejects: set[Any] = set()

            for scope_span in resource_span.get("scopeSpans", []):
                for span_data in scope_span.get("spans", []):
                    span_index = total_spans
                    total_spans += 1
                    trace_key = (
                        span_data.get("traceId")
                        if isinstance(span_data, dict)
                        else None
                    )
                    if span_ingest_bytes is not None:
                        trace_bytes[trace_key] = (
                            trace_bytes.get(trace_key, 0)
                            + span_ingest_bytes[span_index]
                        )

                    if trace_key in foreign_traces:
                        rejected_spans += 1
                        rejected_reasons.append(
                            "Rejected span: its trace belongs to a different task "
                            "than this API key's.",
                        )
                        continue

                    try:
                        # Pass the resolved task ID and resource_id to the span processing
                        processed_span = self._process_span_data(
                            span_data,
                            resolved_task_id,
                            resource_id,
                            resolved_org_id,
                            ingest_bytes=(
                                span_ingest_bytes[span_index]
                                if span_ingest_bytes is not None
                                else None
                            ),
                        )
                        spans_data.append(processed_span)
                        trace_stored.setdefault(trace_key, []).append(processed_span)
                        accepted_spans += 1
                    except Exception as e:
                        rejected_spans += 1
                        traces_with_rejects.add(trace_key)
                        error_msg = f"Invalid span data format: {str(e)}"
                        rejected_reasons.append(error_msg)
                        logger.error(
                            f"Rejected span due to error: {str(e)}\nSpan data keys: {list(span_data.keys()) if isinstance(span_data, dict) else 'not a dict'}",
                            exc_info=True,
                        )

            # A rejected span's share would otherwise be lost: its bytes were still
            # received, so spread them over the stored spans of the same trace in
            # this resource span, which share its trace, task and org. If every span
            # of that trace was rejected, nothing is stored for it, and its bytes
            # stay unattributed rather than credited to another trace.
            if span_ingest_bytes is not None:
                for trace_key in traces_with_rejects:
                    stored = trace_stored.get(trace_key)
                    if not stored:
                        continue
                    shares = self._split_by_weight(
                        trace_bytes[trace_key],
                        [float(span.ingest_bytes or 0) for span in stored],
                    )
                    for span, share in zip(stored, shares, strict=True):
                        span.ingest_bytes = share

        return spans_data, (
            total_spans,
            accepted_spans,
            rejected_spans,
            rejected_reasons,
        )

    def _traces_owned_by_other_tasks(
        self,
        resource_span: dict[str, Any],
        task_id: str,
    ) -> set[Any]:
        """Raw traceIds in this resource span whose trace is already stored under
        a task other than `task_id`."""
        hex_by_raw: dict[Any, str] = {}
        for scope_span in resource_span.get("scopeSpans", []):
            for span_data in scope_span.get("spans", []):
                raw = span_data.get("traceId") if isinstance(span_data, dict) else None
                if not raw or raw in hex_by_raw:
                    continue
                try:
                    hex_by_raw[raw] = trace_utils.convert_id_to_hex(raw)
                except ValueError:
                    # Malformed ids are rejected later by _process_span_data.
                    continue
        if not hex_by_raw:
            return set()
        owned_elsewhere = set(
            self.db_session.execute(
                select(DatabaseTraceMetadata.trace_id).where(
                    DatabaseTraceMetadata.trace_id.in_(set(hex_by_raw.values())),
                    DatabaseTraceMetadata.task_id != task_id,
                ),
            ).scalars(),
        )
        return {raw for raw, hex_id in hex_by_raw.items() if hex_id in owned_elsewhere}

    def _extract_task_id_from_resource_attributes(
        self,
        resource_span: dict[str, Any],
    ) -> str | None:
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

    def _extract_all_resource_attributes(
        self,
        resource_span: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract all resource attributes as a dictionary."""
        attributes = resource_span.get("resource", {}).get("attributes", [])
        result = {}

        for attr in attributes:
            if isinstance(attr, dict):
                key = attr.get("key")
                value = self._extract_value_from_otel_format(attr.get("value", {}))
                if key and value is not None:
                    result[key] = value

        return result

    def _create_or_get_resource_metadata(
        self,
        resource_attributes: dict[str, Any],
        service_name: str | None,
    ) -> str:
        """Create or retrieve resource metadata record."""
        resource_repo = ResourceMetadataRepository(self.db_session)
        return resource_repo.create_or_get_resource(resource_attributes, service_name)

    def _resolve_task_id(
        self,
        explicit_task_id: str | None,
        service_name: str | None,
        resource_attributes: dict[str, Any] | None = None,
    ) -> str:
        """Resolve task_id using priority hierarchy.

        Priority order:
        1. If explicit_task_id (arthur.task) present → use it
        2. If service.name present → lookup in service_name_task_mappings
        3. If mapping found → return mapped task_id
        4. If no mapping but cloud.resource_id present → match by GCP engine ID
        5. If GCP match found → create service_name mapping for future speed, return task_id
        6. If no match → auto-create task and mapping, return new task_id
        7. If no service.name → return __unmapped__ task_id

        Args:
            explicit_task_id: Task ID from arthur.task resource attribute
            service_name: Service name from service.name resource attribute
            resource_attributes: All resource attributes from the trace

        Returns:
            Resolved task_id (never None after migration)
        """
        # Step 1: If explicit_task_id (arthur.task) present → use it
        if explicit_task_id:
            logger.debug(f"Using explicit task_id: {explicit_task_id}")
            try:
                task = self.task_repo.get_db_task_by_id(
                    explicit_task_id,
                    include_archived=True,
                )
                if task.archived:
                    logger.warning(
                        f"Trace received with explicit task ID '{explicit_task_id}' which is archived. "
                        "Traces are still being written to this task. "
                        "Unarchive the task to resume normal operation.",
                    )
            except Exception as e:
                logger.debug(
                    f"Could not check archived status for task '{explicit_task_id}': {e}",
                )
            return explicit_task_id

        # Step 2: If no task_id but service.name present → lookup in mapping
        if service_name and service_name.strip() != "":
            mapping_repo = ServiceNameMappingRepository(self.db_session)
            existing_task_id = mapping_repo.get_task_id_by_service_name(service_name)

            # Step 3: If lookup finds mapping → return mapped task_id
            if existing_task_id:
                logger.debug(
                    f"Found existing mapping: {service_name} → {existing_task_id}",
                )
                # Check if the mapped task is archived — warn but still route to it
                try:
                    mapped_task = self.task_repo.get_db_task_by_id(
                        existing_task_id,
                        include_archived=True,
                    )
                    if mapped_task.archived:
                        logger.warning(
                            f"Service name '{service_name}' is mapped to archived task "
                            f"{existing_task_id}. Traces are still being written to this task. "
                            "Unarchive the task to resume normal operation.",
                        )
                except Exception as e:
                    logger.debug(
                        f"Could not check archived status for task '{existing_task_id}': {e}",
                    )
                return existing_task_id

            # Step 4: Check resource attributes for GCP cloud.resource_id
            if resource_attributes:
                cloud_resource_id = resource_attributes.get("cloud.resource_id")
                if cloud_resource_id:
                    try:
                        _, _, engine_id = parse_gcp_resource_path(cloud_resource_id)
                        if engine_id:
                            existing_task = self.task_repo.find_by_gcp_engine_id(
                                engine_id,
                            )
                            if existing_task:
                                if existing_task.archived:
                                    logger.warning(
                                        f"Service name '{service_name}' matched GCP task "
                                        f"'{existing_task.name}' ({existing_task.id}) which is archived. "
                                        "Traces are still being written to this task. "
                                        "Unarchive the task to resume normal operation.",
                                    )
                                # Step 5: Create service_name mapping for future speed
                                mapping_repo.create_mapping(
                                    service_name,
                                    existing_task.id,
                                )
                                logger.info(
                                    f"Matched service.name='{service_name}' to existing GCP task "
                                    f"'{existing_task.name}' (id={existing_task.id}) via cloud.resource_id",
                                )
                                return existing_task.id
                    except Exception as e:
                        logger.warning(
                            f"Failed to match cloud.resource_id '{cloud_resource_id}': {e}",
                        )

            # Step 6: If no mapping and no GCP match → auto-create task and mapping
            logger.info(
                f"No mapping found for service.name='{service_name}'. Auto-creating task.",
            )

            try:
                new_task = self.task_repo.create_auto_task(service_name)

                mapping_repo.create_mapping(service_name, new_task.id)

                logger.info(f"Auto-created task '{new_task.name}' (id={new_task.id})")
                return new_task.id

            except Exception as e:
                # Fall back to __unmapped__ task - never reject traces
                logger.error(
                    f"Failed to auto-create task for '{service_name}': {e}",
                    exc_info=True,
                )
                return UNMAPPED_TASK_ID

        # Step 7: If no service.name → return __unmapped__ task_id
        logger.debug(f"No service.name provided, using UNMAPPED_TASK_ID")
        return UNMAPPED_TASK_ID

    def _process_span_data(
        self,
        span_data: dict[str, Any],
        resource_task_id: str,
        resource_id: str | None = None,
        resource_org_id: uuid.UUID = DEFAULT_ORG_ID,
        ingest_bytes: int | None = None,
    ) -> DatabaseSpan:
        """Process and clean span data, returning None if the span data is invalid."""
        span_data = self._normalize_span_attributes(span_data)
        # Inject version into raw data
        span_data[SPAN_VERSION_KEY] = EXPECTED_SPAN_VERSION
        start_time, end_time = self._extract_timestamps(span_data)

        # Extract and normalize status code (handle nested structure after normalization)
        status = span_data.get("status")
        if isinstance(status, dict):
            status_code = status.get("code", "Unset")
        elif isinstance(status, list) and len(status) > 0:
            # If status was converted to list (shouldn't happen but handle it)
            if isinstance(status[0], (str, int)):
                status_code = str(
                    status[0],
                )
            elif isinstance(status[0], dict):
                status_code = status[0].get("code", "Unset")
            else:
                status_code = "Unset"
        else:
            status_code = trace_utils.get_nested_value(
                span_data,
                "status.code",
                default="Unset",
            )
        span_status_code = trace_utils.clean_status_code(status_code)

        # Extract token/cost info (fast - from attributes only, compute cost if needed)
        span_kind = self._get_attribute_value(span_data, SPAN_KIND_KEY)
        token_data = trace_utils.extract_token_cost_from_span(span_data, span_kind)

        return DatabaseSpan(
            id=str(uuid.uuid4()),
            trace_id=trace_utils.convert_id_to_hex(span_data.get("traceId", "")),
            span_id=trace_utils.convert_id_to_hex(span_data.get("spanId", "")),
            parent_span_id=self._get_parent_span_id(span_data),
            span_kind=span_kind,
            span_name=span_data.get("name"),
            start_time=start_time,
            end_time=end_time,
            task_id=resource_task_id,
            org_id=resource_org_id,
            resource_id=resource_id,
            session_id=self._get_attribute_value(span_data, SpanAttributes.SESSION_ID),
            user_id=self._get_attribute_value(span_data, USER_ID_KEY),
            status_code=span_status_code,
            raw_data=span_data,
            prompt_token_count=token_data.prompt_token_count,
            completion_token_count=token_data.completion_token_count,
            total_token_count=token_data.total_token_count,
            prompt_token_cost=token_data.prompt_token_cost,
            completion_token_cost=token_data.completion_token_cost,
            total_token_cost=token_data.total_token_cost,
            ingest_bytes=ingest_bytes,
        )

    def _extract_value_from_otel_format(
        self,
        value_dict: dict[str, Any],
    ) -> str | int | float | bool | None:
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
        try:
            if "stringValue" in value_dict:
                return str(value_dict["stringValue"])
            elif "intValue" in value_dict:
                return int(value_dict["intValue"])
            elif "doubleValue" in value_dict:
                return float(value_dict["doubleValue"])
            elif "boolValue" in value_dict:
                if isinstance(value_dict["boolValue"], bool):
                    return value_dict["boolValue"]
                else:
                    return bool(str(value_dict["boolValue"]).lower() == "true")
            else:
                return None
        except (ValueError, TypeError):
            return None

    def _is_valid_task_id(self, task_id: str) -> bool:
        """Validate that a task ID is a non-empty string."""
        return isinstance(task_id, str) and bool(task_id.strip())

    def _normalize_span_attributes(self, span_data: dict[str, Any]) -> dict[str, Any]:
        """Normalize span to nested dictionary structure with selective JSON deserialization."""
        return self.span_normalizer.normalize_span_to_nested_dict(span_data)

    def _get_attribute_value(
        self,
        span_data: dict[str, Any],
        attribute_key: str,
    ) -> str | None:
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
                    return (
                        str(value.get("stringValue"))
                        if value.get("stringValue") is not None
                        else None
                    )

        return None

    def _get_parent_span_id(self, span_data: dict[str, Any]) -> str | None:
        """Extract parent span ID from span data."""
        if "parentSpanId" in span_data:
            return trace_utils.convert_id_to_hex(str(span_data["parentSpanId"]))
        return None

    def _extract_timestamps(
        self,
        span_data: dict[str, Any],
    ) -> tuple[datetime | None, datetime | None]:
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

    def _store_spans(self, spans: list[DatabaseSpan], commit: bool = True) -> None:
        """Store spans in the database with optional commit control."""
        if not spans:
            return

        self.db_session.add_all(spans)
        self._batch_upsert_trace_metadata(spans)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans with trace metadata (commit={commit})")

    def _batch_upsert_trace_metadata(self, spans: list[DatabaseSpan]) -> None:
        """Efficiently batch trace metadata updates using native database upsert.

        Groups spans by trace_id to batch updates. For example:
        - 50 spans from same trace = 1 upsert (not 50!)
        - Handles out-of-order span arrival with MIN/MAX aggregations
        - Uses native PostgreSQL/SQLite upsert for optimal performance
        """
        if not spans:
            return

        # Group spans by trace_id to batch updates
        trace_updates: dict[str, TraceUpdateDict] = {}
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

                trace_updates[trace_id] = TraceUpdateDict(
                    trace_id=trace_id,
                    task_id=span.task_id,
                    org_id=span.org_id,
                    root_span_resource_id=None,  # Will be populated from earliest root span
                    session_id=span.session_id,
                    user_id=span.user_id,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    span_count=0,
                    updated_at=current_time,
                    input_content=None,
                    output_content=None,
                    earliest_root_start_time=None,  # Track time of earliest root span
                    prompt_token_count=None,
                    completion_token_count=None,
                    total_token_count=None,
                    prompt_token_cost=None,
                    completion_token_cost=None,
                    total_token_cost=None,
                    ingest_bytes=None,
                )

            # Aggregate within this batch (handles multiple spans per trace in one ingestion)
            trace_updates[trace_id]["start_time"] = min(
                trace_updates[trace_id]["start_time"],
                span.start_time,
            )
            trace_updates[trace_id]["end_time"] = max(
                trace_updates[trace_id]["end_time"],
                span.end_time,
            )
            trace_updates[trace_id]["span_count"] = safe_add(
                trace_updates[trace_id]["span_count"],
                1,
            )

            # Handle session_id conflicts: use first non-null session_id found
            if span.session_id and not trace_updates[trace_id]["session_id"]:
                trace_updates[trace_id]["session_id"] = span.session_id

            # Handle user_id conflicts: use first non-null user_id found
            if span.user_id and not trace_updates[trace_id]["user_id"]:
                trace_updates[trace_id]["user_id"] = span.user_id

            # Extract input/output from root spans (no parent_span_id)
            # Only use the earliest root span for each trace
            if not span.parent_span_id:
                # Store root span's resource_id (first non-null value)
                if (
                    span.resource_id
                    and not trace_updates[trace_id]["root_span_resource_id"]
                ):
                    trace_updates[trace_id]["root_span_resource_id"] = span.resource_id

                earliest_time = trace_updates[trace_id]["earliest_root_start_time"]
                if earliest_time is None or span.start_time < earliest_time:
                    # This is the earliest root span so far, extract its input/output
                    trace_updates[trace_id][
                        "earliest_root_start_time"
                    ] = span.start_time

                    # Extract and convert to string for database storage
                    # Using OpenInference semantic convention constants on attributes dict
                    attributes = span.raw_data.get("attributes", {})
                    input_value = trace_utils.get_nested_value(
                        attributes,
                        SpanAttributes.INPUT_VALUE,
                    )
                    output_value = trace_utils.get_nested_value(
                        attributes,
                        SpanAttributes.OUTPUT_VALUE,
                    )

                    trace_updates[trace_id]["input_content"] = (
                        trace_utils.value_to_string(input_value)
                    )
                    trace_updates[trace_id]["output_content"] = (
                        trace_utils.value_to_string(output_value)
                    )

            for field in [*TOKEN_FIELDS, "ingest_bytes"]:
                span_value = getattr(span, field)
                trace_updates[trace_id][field] = safe_add(  # type: ignore[literal-required]
                    trace_updates[trace_id][field],  # type: ignore[literal-required]
                    span_value,
                )

        if not trace_updates:
            return

        # Remove tracking field before database upsert (not a database column)
        # Create copies without earliest_root_start_time for database insertion
        values_list: list[TraceUpdateDBBase] = [
            {k: v for k, v in trace_data.items() if k != "earliest_root_start_time"}  # type: ignore[misc]
            for trace_data in trace_updates.values()
        ]
        stmt: PGInsertType | SQLiteInsertType

        # PostgreSQL upsert with proper aggregation functions
        if self.db_session.bind and self.db_session.bind.dialect.name == "postgresql":
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

    def _build_upsert_set_dict(
        self,
        stmt: PGInsertType | SQLiteInsertType,
        min_func: Callable[
            [
                ColumnElement[Any] | InstrumentedAttribute[Any],
                ColumnElement[Any] | InstrumentedAttribute[Any],
            ],
            ColumnElement[Any],
        ],
        max_func: Callable[
            [
                ColumnElement[Any] | InstrumentedAttribute[Any],
                ColumnElement[Any] | InstrumentedAttribute[Any],
            ],
            ColumnElement[Any],
        ],
    ) -> dict[str, ColumnElement[Any]]:
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
            ingest_bytes=func.coalesce(
                DatabaseTraceMetadata.ingest_bytes + stmt.excluded.ingest_bytes,
                DatabaseTraceMetadata.ingest_bytes,
                stmt.excluded.ingest_bytes,
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
