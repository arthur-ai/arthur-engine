from datetime import datetime
from typing import Optional

from arthur_common.models.response_schemas import (
    ExternalInference,
    MetricResponse,
    SpanResponse,
)
from pydantic import BaseModel, Field


# Internal to genai-engine
class DocumentStorageConfigurationResponse(BaseModel):
    storage_environment: Optional[str] = None
    bucket_name: Optional[str] = None
    container_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None


# Internal to genai-engine
class ApplicationConfigurationResponse(BaseModel):
    chat_task_id: Optional[str] = None
    document_storage_configuration: Optional[DocumentStorageConfigurationResponse] = (
        None
    )
    max_llm_rules_per_task_count: int


# Internal to genai-engine
class ConversationBaseResponse(BaseModel):
    id: str
    updated_at: datetime


# Internal to genai-engine
class ConversationResponse(ConversationBaseResponse):
    inferences: list[ExternalInference]


# Internal to genai-engine
class HealthResponse(BaseModel):
    message: str
    build_version: Optional[str] = None


# Internal to genai-engine
class ComputeMetricsFiltersResponse(BaseModel):
    start_time: Optional[datetime] = Field(
        description="Start time filter applied",
        default=None,
    )
    end_time: Optional[datetime] = Field(
        description="End time filter applied",
        default=None,
    )
    conversation_id: Optional[str] = Field(
        description="Conversation ID filter applied",
        default=None,
    )
    user_id: Optional[str] = Field(description="User ID filter applied", default=None)
    page: int = Field(description="Page number used for pagination")
    page_size: int = Field(description="Page size used for pagination")


# Internal to genai-engine
class ComputeMetricsResponse(BaseModel):
    task_id: str = Field(description="ID of the task for which metrics were computed")
    metrics: list[MetricResponse] = Field(
        description="List of metrics associated with the task",
    )
    span_count: int = Field(description="Number of spans matching the filters")
    spans: list[SpanResponse] = Field(
        description="List of spans used for metric computation",
    )
    filters_applied: ComputeMetricsFiltersResponse = Field(
        description="Filters that were applied to the data",
    )
