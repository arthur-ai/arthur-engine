from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from arthur_common.models.response_schemas import (
    ExternalInference,
    TokenCountCostSchema,
    TraceResponse,
)
from litellm.types.utils import ChatCompletionMessageToolCall
from pydantic import BaseModel, Field
from pydantic_core import Url

from schemas.enums import (
    ConnectionCheckOutcome,
    ModelProvider,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
    RagProviderEnum,
)


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


class DatasetResponse(BaseModel):
    id: UUID = Field(description="ID of the dataset.")
    name: str = Field(
        description="Name of the dataset.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the dataset.",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Any metadata to include that describes additional information about the dataset.",
    )
    created_at: int = Field(
        description="Timestamp representing the time of dataset creation in unix milliseconds.",
    )
    updated_at: int = Field(
        description="Timestamp representing the time of the last dataset update in unix milliseconds.",
    )
    latest_version_number: Optional[int] = Field(
        default=None,
        description="Version number representing the latest version of the dataset. If unset, no versions exist for the dataset yet.",
    )


class SearchDatasetsResponse(BaseModel):
    count: int = Field(
        description="The total number of datasets matching the parameters.",
    )
    datasets: list[DatasetResponse] = Field(
        description="List of datasets matching the search filters. Length is less than or equal to page_size parameter",
    )


class DatasetVersionRowColumnItemResponse(BaseModel):
    column_name: str = Field(description="Name of the column.")
    column_value: str = Field(description="Value of the column.")


class DatasetVersionRowResponse(BaseModel):
    id: UUID = Field(description="ID of the version field.")
    data: List[DatasetVersionRowColumnItemResponse] = Field(
        description="List of column names and values in the row.",
    )
    created_at: int = Field(
        description="Timestamp representing the time of dataset row creation in unix milliseconds. May differ within "
        "a version if a row already existed in a past version of the dataset.",
    )


class DatasetVersionMetadataResponse(BaseModel):
    version_number: int = Field(description="Version number of the dataset version.")
    created_at: int = Field(
        description="Timestamp representing the time of dataset version creation in unix milliseconds.",
    )
    dataset_id: UUID = Field(description="ID of the dataset.")
    column_names: List[str] = Field(
        description="Names of all columns in the dataset version.",
    )


class DatasetVersionResponse(DatasetVersionMetadataResponse):
    rows: list[DatasetVersionRowResponse] = Field(
        description="list of rows in the dataset version.",
    )
    page: int = Field(description="The current page number for the included rows.")
    page_size: int = Field(description="The number of rows per page.")
    total_pages: int = Field(description="The total number of pages.")
    total_count: int = Field(
        description="The total number of rows in the dataset version.",
    )


class ListDatasetVersionsResponse(BaseModel):
    versions: List[DatasetVersionMetadataResponse] = Field(
        description="List of existing versions for the dataset.",
    )
    page: int = Field(description="The current page number for the included rows.")
    page_size: int = Field(description="The number of rows per page.")
    total_pages: int = Field(description="The total number of pages.")
    total_count: int = Field(
        description="The total number of rows in the dataset version.",
    )


class TraceMetadataResponse(TokenCountCostSchema):
    """Lightweight trace metadata for list operations"""

    trace_id: str = Field(description="ID of the trace")
    task_id: str = Field(description="Task ID this trace belongs to")
    user_id: Optional[str] = Field(None, description="User ID if available")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    start_time: datetime = Field(description="Start time of the earliest span")
    end_time: datetime = Field(description="End time of the latest span")
    span_count: int = Field(description="Number of spans in this trace")
    duration_ms: float = Field(description="Total trace duration in milliseconds")
    created_at: datetime = Field(description="When the trace was first created")
    updated_at: datetime = Field(description="When the trace was last updated")
    input_content: Optional[str] = Field(
        None,
        description="Root span input value from trace metadata",
    )
    output_content: Optional[str] = Field(
        None,
        description="Root span output value from trace metadata",
    )


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
    user_id: Optional[str] = Field(None, description="User ID if available")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    status_code: str = Field(description="Status code (Unset, Error, Ok)")
    created_at: datetime = Field(description="When the span was created")
    updated_at: datetime = Field(description="When the span was updated")
    input_content: Optional[str] = Field(
        None,
        description="Span input value from raw_data.attributes.input.value",
    )
    output_content: Optional[str] = Field(
        None,
        description="Span output value from raw_data.attributes.output.value",
    )
    # Note: Excludes raw_data, computed features, and metrics for performance


class SessionMetadataResponse(TokenCountCostSchema):
    """Session summary metadata"""

    session_id: str = Field(description="Session identifier")
    task_id: str = Field(description="Task ID this session belongs to")
    user_id: Optional[str] = Field(None, description="User ID if available")
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


class TraceUserMetadataResponse(TokenCountCostSchema):
    """User summary metadata in trace context"""

    user_id: str = Field(description="User identifier")
    task_id: str = Field(description="Task ID this user belongs to")
    session_ids: list[str] = Field(description="List of session IDs for this user")
    session_count: int = Field(description="Number of sessions for this user")
    trace_ids: list[str] = Field(description="List of trace IDs for this user")
    trace_count: int = Field(description="Number of traces for this user")
    span_count: int = Field(description="Total number of spans for this user")
    earliest_start_time: datetime = Field(description="Start time of earliest trace")
    latest_end_time: datetime = Field(description="End time of latest trace")


class TraceUserListResponse(BaseModel):
    """Response for trace user list endpoint"""

    count: int = Field(description="Total number of users matching filters")
    users: list[TraceUserMetadataResponse] = Field(description="List of user metadata")


class AgenticPromptRunResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    cost: str


class ModelProviderResponse(BaseModel):
    provider: ModelProvider = Field(description="The model provider")
    enabled: bool = Field(
        description="Whether the provider is enabled with credentials",
    )


class ModelProviderList(BaseModel):
    providers: list[ModelProviderResponse] = Field(
        description="List of model providers",
    )


class ModelProviderModelList(BaseModel):
    provider: ModelProvider = Field(description="Provider of the models")
    available_models: List[str] = Field(
        description="Available models from the provider",
    )


class ApiKeyRagAuthenticationConfigResponse(BaseModel):
    authentication_method: Literal[
        RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    ] = RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    host_url: Url = Field(description="URL of host instance to authenticate with.")
    rag_provider: RagAPIKeyAuthenticationProviderEnum = Field(
        description="Name of RAG provider to authenticate with.",
    )


RagAuthenticationConfigResponseTypes = Union[ApiKeyRagAuthenticationConfigResponse]


class RagProviderConfigurationResponse(BaseModel):
    id: UUID = Field(description="Unique identifier of the RAG provider configuration.")
    task_id: str = Field(description="ID of parent task.")
    authentication_config: RagAuthenticationConfigResponseTypes = Field(
        description="Configuration of the authentication strategy.",
    )
    name: str = Field(description="Name of RAG provider configuration.")
    description: Optional[str] = Field(
        default=None,
        description="Description of RAG provider configuration.",
    )
    created_at: int = Field(
        description="Time the RAG provider configuration was created in unix milliseconds",
    )
    updated_at: int = Field(
        description="Time the RAG provider configuration was updated in unix milliseconds",
    )


class SearchRagProviderConfigurationsResponse(BaseModel):
    count: int = Field(
        description="The total number of RAG provider configurations matching the parameters.",
    )
    rag_provider_configurations: list[RagProviderConfigurationResponse] = Field(
        description="List of RAG provider configurations matching the search filters. Length is less than or equal to page_size parameter",
    )


class RagProviderCollectionResponse(BaseModel):
    identifier: str = Field(description="Unique identifier of the collection.")
    description: Optional[str] = Field(
        default=None,
        description="Description of the collection.",
    )


class SearchRagProviderCollectionsResponse(BaseModel):
    count: int = Field(
        description="The total number of RAG provider collections matching the parameters.",
    )
    rag_provider_collections: list[RagProviderCollectionResponse]


class ConnectionCheckResult(BaseModel):
    connection_check_outcome: ConnectionCheckOutcome = Field(
        description="Result of the connection check.",
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Explainer of the connection check failure result.",
    )


class WeaviateQueryResultMetadata(BaseModel):
    """
    Metadata from weaviate for a vector object:
    https://weaviate-python-client.readthedocs.io/en/latest/weaviate.collections.classes.html#module-weaviate.collections.classes.internal
    """

    creation_time: Optional[datetime] = Field(
        default=None,
        description="Vector object creation time.",
    )
    last_update_time: Optional[datetime] = Field(
        default=None,
        description="Vector object last update time.",
    )
    distance: Optional[float] = Field(
        default=None,
        description="Raw distance metric used in the vector search. Lower values indicate closer vectors.",
    )
    certainty: Optional[float] = Field(
        default=None,
        description="Similarity score measure between 0 and 1. Higher values correspond to more similar reesults.",
    )
    score: Optional[float] = Field(
        default=None,
        description="Normalized relevance metric that ranks search results.",
    )
    explain_score: Optional[str] = Field(
        default=None,
        description="Explanation of how the score was calculated.",
    )
    is_consistent: Optional[bool] = Field(
        default=None,
        description="Indicates if the object is consistent across all replicates in a multi-node Weaviate cluster.",
    )


class WeaviateQueryResult(BaseModel):
    """Individual search result from Weaviate"""

    uuid: UUID = Field(description="Unique identifier of the result")
    metadata: Optional[WeaviateQueryResultMetadata] = Field(
        default=None,
        description="Search metadata including distance, score, etc.",
    )
    # left out references for now
    properties: Dict[str, Any] = Field(description="Properties of the result object")
    vector: Optional[Dict[str, Union[List[float], List[List[float]]]]] = Field(
        default=None,
        description="Vector representation",
    )


class WeaviateQueryResults(BaseModel):
    """Response from Weaviate similarity text search"""

    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE
    objects: List[WeaviateQueryResult] = Field(
        description="List of search result objects",
    )


RagProviderSimilarityTextSearchResponseTypes = Union[WeaviateQueryResults]


class RagProviderQueryResponse(BaseModel):
    response: RagProviderSimilarityTextSearchResponseTypes


class AgenticPromptMetadataResponse(BaseModel):
    name: str = Field(description="Name of the prompt")
    versions: int = Field(description="Number of versions of the prompt")
    created_at: datetime = Field(description="Timestamp when the prompt was created")
    latest_version_created_at: datetime = Field(
        description="Timestamp when the last version of the prompt was created",
    )
    deleted_versions: List[int] = Field(
        description="List of deleted versions of the prompt",
    )


class AgenticPromptMetadataListResponse(BaseModel):
    prompt_metadata: list[AgenticPromptMetadataResponse] = Field(
        description="List of prompt metadata",
    )
    count: int = Field(description="Total number of prompts matching filters")


class AgenticPromptVersionResponse(BaseModel):
    version: int = Field(description="Version number of the prompt")
    created_at: datetime = Field(
        description="Timestamp when the prompt version was created",
    )
    deleted_at: Optional[datetime] = Field(
        description="Timestamp when the prompt version was deleted",
    )
    model_provider: ModelProvider = Field(description="Model provider of the prompt")
    model_name: str = Field(description="Model name of the prompt")
    num_messages: int = Field(description="Number of messages in the prompt")
    num_tools: int = Field(description="Number of tools in the prompt")


class AgenticPromptVersionListResponse(BaseModel):
    versions: list[AgenticPromptVersionResponse] = Field(
        description="List of prompt version metadata",
    )
    count: int = Field(description="Total number of prompts matching filters")
