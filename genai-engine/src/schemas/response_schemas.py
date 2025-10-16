from datetime import datetime
from typing import List, Optional

from arthur_common.models.response_schemas import ExternalInference, TraceResponse
from litellm.types.utils import ChatCompletionMessageToolCall
from pydantic import BaseModel, Field


class DocumentStorageConfigurationResponse(BaseModel):
    storage_environment: Optional[str] = None
    bucket_name: Optional[str] = None
    container_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None


class ApplicationConfigurationResponse(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[DocumentStorageConfigurationResponse] = (
        None
    )
    max_llm_rules_per_task_count: int


class ConversationBaseResponse(BaseModel):
    id: str
    updated_at: datetime


class ConversationResponse(ConversationBaseResponse):
    inferences: list[ExternalInference]


class HealthResponse(BaseModel):
    message: str
    build_version: Optional[str] = None


class TraceMetadataResponse(BaseModel):
    """Lightweight trace metadata for list operations"""

    trace_id: str = Field(description="ID of the trace")
    task_id: str = Field(description="Task ID this trace belongs to")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    start_time: datetime = Field(description="Start time of the earliest span")
    end_time: datetime = Field(description="End time of the latest span")
    span_count: int = Field(description="Number of spans in this trace")
    duration_ms: float = Field(description="Total trace duration in milliseconds")
    created_at: datetime = Field(description="When the trace was first created")
    updated_at: datetime = Field(description="When the trace was last updated")


class SpanMetadataResponse(BaseModel):
    """Lightweight span metadata for list operations"""

    id: str = Field(description="Internal database ID")
    trace_id: str = Field(description="ID of the parent trace")
    span_id: str = Field(description="OpenTelemetry span ID")
    parent_span_id: Optional[str] = Field(None, description="Parent span ID")
    span_kind: Optional[str] = Field(None, description="Type of span (LLM, TOOL, etc.)")
    span_name: Optional[str] = Field(None, description="Human-readable span name")
    start_time: datetime = Field(description="Span start time")
    end_time: datetime = Field(description="Span end time")
    duration_ms: float = Field(description="Span duration in milliseconds")
    task_id: Optional[str] = Field(None, description="Task ID this span belongs to")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    status_code: str = Field(description="Status code (Unset, Error, Ok)")
    created_at: datetime = Field(description="When the span was created")
    updated_at: datetime = Field(description="When the span was updated")
    # Note: Excludes raw_data, computed features, and metrics for performance


class SessionMetadataResponse(BaseModel):
    """Session summary metadata"""

    session_id: str = Field(description="Session identifier")
    task_id: str = Field(description="Task ID this session belongs to")
    trace_ids: list[str] = Field(description="List of trace IDs in this session")
    trace_count: int = Field(description="Number of traces in this session")
    span_count: int = Field(description="Total number of spans in this session")
    earliest_start_time: datetime = Field(description="Start time of earliest trace")
    latest_end_time: datetime = Field(description="End time of latest trace")
    duration_ms: float = Field(description="Total session duration in milliseconds")


class TraceListResponse(BaseModel):
    """Response for trace list endpoint"""

    count: int = Field(description="Total number of traces matching filters")
    traces: list[TraceMetadataResponse] = Field(description="List of trace metadata")


class SpanListResponse(BaseModel):
    """Response for span list endpoint"""

    count: int = Field(description="Total number of spans matching filters")
    spans: list[SpanMetadataResponse] = Field(description="List of span metadata")


class SessionListResponse(BaseModel):
    """Response for session list endpoint"""

    count: int = Field(description="Total number of sessions matching filters")
    sessions: list[SessionMetadataResponse] = Field(
        description="List of session metadata",
    )


class SessionTracesResponse(BaseModel):
    """Response for session traces endpoint"""

    session_id: str = Field(description="Session identifier")
    count: int = Field(description="Number of traces in this session")
    traces: list[TraceResponse] = Field(description="List of full trace trees")


class AgenticPromptRunResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    cost: str
