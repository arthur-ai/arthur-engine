import base64
import json
import logging
import uuid
from datetime import datetime

from db_models.db_models import DatabaseSpan
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from schemas.enums import PaginationSortMethod
from schemas.internal_schemas import Span
from sqlalchemy import and_, asc, desc, insert, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class SpanRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    @tracer.start_as_current_span("store_traces")
    def store_traces(self, trace_data: bytes):
        """
        Process trace data from protobuf format and store in database using bulk insert.

        Args:
            trace_data: Raw protobuf trace data

        Returns:
        tuple: (total_spans, accepted_spans, unnecessary_spans, rejected_spans, rejected_reasons)
        """
        total_spans = 0
        accepted_spans = 0
        unnecessary_spans = 0
        rejected_spans = 0
        rejected_reasons = []

        try:
            # Parse the protobuf message
            json_traces = grpc_trace_to_dict(trace_data)

            # Process each span and prepare data for bulk insert
            spans_data = []
            for resource_span in json_traces.get("resourceSpans", []):
                for scope_span in resource_span.get("scopeSpans", []):
                    for span_data in scope_span.get("spans", []):
                        total_spans += 1
                        if is_llm_span(span_data):
                            span_dict = clean_span_data(span_data)
                            # None if Task ID missing. This raises a warning
                            if span_dict:
                                span_dict["id"] = str(uuid.uuid4())
                                spans_data.append(span_dict)
                                accepted_spans += 1
                            else:
                                rejected_spans += 1
                                rejected_reasons.append("Missing task ID")
                        else:
                            unnecessary_spans += 1

            if spans_data:
                # Perform bulk insert using SQLAlchemy core
                self.store_spans(spans_data)

            return (
                total_spans,
                accepted_spans,
                unnecessary_spans,
                rejected_spans,
                rejected_reasons,
            )

        except DecodeError as e:
            raise DecodeError("Failed to parse protobuf message.") from e

    def query_spans(
        self,
        sort: PaginationSortMethod,
        page: int,
        page_size: int = 10,
        trace_ids: list[str] = None,
        span_ids: list[str] = None,
        task_ids: list[str] = None,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> list[Span]:
        """
        Query spans with efficient filtering and pagination.
        Only loads necessary fields and applies filters at the database level.
        """
        # Build the query
        query = build_spans_query(
            trace_ids=trace_ids,
            span_ids=span_ids,
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        # Execute query and transform results
        results = self.db_session.execute(query).scalars().all()
        return [Span._from_database_model(span) for span in results]

    def store_spans(self, spans: list[Span]):
        """
        Store spans in the database
        """
        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)
        self.db_session.commit()
        logger.debug(f"Stored {len(spans)} spans")


###########
# HELPERS #
###########


def grpc_trace_to_dict(trace_data: bytes):
    try:
        trace_request = ExportTraceServiceRequest()
        trace_request.ParseFromString(trace_data)
        json_traces = MessageToDict(trace_request)
        return json_traces
    except DecodeError as e:
        raise DecodeError("Failed to decode protobuf message.") from e


def convert_id_to_hex(id: str):
    """
    Convert a base64 encoded ID to a hex string
    """
    return base64.b64decode(id).hex()


def is_llm_span(span_data):
    """Check if a span is an LLM span"""
    if "attributes" not in span_data:
        return False

    for attr in span_data.get("attributes", []):
        key = attr.get("key")
        value = attr.get("value", {})
        if key == "openinference.span.kind" and value.get("stringValue") == "LLM":
            return True
    return False


def extract_timestamps(span_data):
    """Extract and convert timestamps from span data"""
    start_time = None
    end_time = None

    if "startTimeUnixNano" in span_data:
        start_time_ns = int(span_data.get("startTimeUnixNano", 0))
        start_time = timestamp_ns_to_datetime(start_time_ns)

    if "endTimeUnixNano" in span_data:
        end_time_ns = int(span_data.get("endTimeUnixNano", 0))
        end_time = timestamp_ns_to_datetime(end_time_ns)
    return start_time, end_time


def get_task_id(metadata: dict):
    """
    Get the task ID from the metadata
    Return None if the task ID is not present
    """
    return metadata.get("arthur.task", None)


def get_metadata(span_data):
    """
    Get the metadata from the span data
    """
    attrs = span_data.get("attributes", [])
    for attr in attrs:
        if attr.get("key") == "metadata":
            return json.loads(attr.get("value").get("stringValue"))
    return {}


def clean_span_data(span_data):
    """
    Clean and process span data, returning None if not an LLM span
    or if the span data is invalid.
    """
    # Extract basic span data
    span_dict = {
        "trace_id": convert_id_to_hex(span_data.get("traceId")),
        "span_id": convert_id_to_hex(span_data.get("spanId")),
    }

    # Extract timestamps
    start_time, end_time = extract_timestamps(span_data)
    span_dict["start_time"] = start_time
    span_dict["end_time"] = end_time

    # Extract attributes and metadata
    metadata = get_metadata(span_data)
    task_id = get_task_id(metadata)
    if not task_id:
        logger.warning(f"No task ID found for span {span_dict['span_id']}. Skipping.")
        return None
    span_dict["task_id"] = task_id
    span_dict["raw_data"] = span_data
    return span_dict


def value_dict_to_value(value: dict):
    """
    Convert a value dictionary to a value
    """
    if "stringValue" in value:
        return value["stringValue"]
    elif "intValue" in value:
        return int(value["intValue"])
    elif "doubleValue" in value:
        return float(value["doubleValue"])
    elif "boolValue" in value:
        return bool(value["boolValue"])
    else:
        return value


# For timestamps in nanoseconds (OpenTelemetry default)
def timestamp_ns_to_datetime(timestamp_ns):
    # Convert nanoseconds to seconds (divide by 1,000,000,000)
    timestamp_s = timestamp_ns / 1_000_000_000
    return datetime.fromtimestamp(timestamp_s)


def build_spans_query(
    page: int,
    trace_ids: list[str] = None,
    span_ids: list[str] = None,
    task_ids: list[str] = None,
    start_time: datetime = None,
    end_time: datetime = None,
    sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
    page_size: int = 10,
) -> select:
    """
    Build a query for spans with the given filters.
    This method only constructs the query without executing it.
    """
    query = select(DatabaseSpan)

    # Build filter conditions
    conditions = []
    if task_ids:
        conditions.append(DatabaseSpan.task_id.in_(task_ids))
    if trace_ids:
        conditions.append(DatabaseSpan.trace_id.in_(trace_ids))
    if span_ids:
        conditions.append(DatabaseSpan.span_id.in_(span_ids))
    if start_time:
        conditions.append(DatabaseSpan.created_at >= start_time)
    if end_time:
        conditions.append(DatabaseSpan.created_at <= end_time)

    # Apply filters if any conditions exist
    if conditions:
        query = query.where(and_(*conditions))

    # Apply sorting
    if sort == PaginationSortMethod.DESCENDING:
        query = query.order_by(desc(DatabaseSpan.created_at))
    elif sort == PaginationSortMethod.ASCENDING:
        query = query.order_by(asc(DatabaseSpan.created_at))

    # Apply pagination
    if page is not None and page_size is not None:
        query = query.offset(page * page_size).limit(page_size)

    return query
