import uuid
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
from weaviate.collections.classes.grpc import (
    METADATA,
    HybridFusion,
    TargetVectorJoinType,
)
from weaviate.types import INCLUDE_VECTOR

from schemas.enums import (
    ConnectionCheckOutcome,
    ModelProvider,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
    RagProviderEnum,
    RagSearchKind,
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


class SpanMetadataResponse(TokenCountCostSchema):
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


class WeaviateSearchCommonSettingsResponse(BaseModel):
    collection_name: str = Field(
        description="Name of the vector collection used for the search.",
    )
    limit: Optional[int] = Field(
        default=None,
        description="Maximum number of objects to return.",
    )
    include_vector: Optional[INCLUDE_VECTOR] = Field(
        default=False,
        description="Boolean value whether to include vector embeddings in the response or can be used to specify the names of the vectors to include in the response if your collection uses named vectors. Will be included as a dictionary in the vector property in the response.",
    )
    offset: Optional[int] = Field(
        default=None,
        description="Skips first N results in similarity response. Useful for pagination.",
    )
    auto_limit: Optional[int] = Field(
        default=None,
        description="Automatically limit search results to groups of objects with similar distances, stopping after auto_limit number of significant jumps.",
    )
    return_metadata: Optional[METADATA] = Field(
        default=None,
        description="Specify metadata fields to return.",
    )
    return_properties: Optional[List[str]] = Field(
        default=None,
        description="Specify which properties to return for each object.",
    )


class WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse(
    WeaviateSearchCommonSettingsResponse,
):
    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE
    search_kind: Literal[RagSearchKind.VECTOR_SIMILARITY_TEXT_SEARCH] = (
        RagSearchKind.VECTOR_SIMILARITY_TEXT_SEARCH
    )

    certainty: Optional[float] = Field(
        default=None,
        description="Minimum similarity score to return. Higher values correspond to more similar results. Only one of distance and certainty can be specified.",
        ge=0,
        le=1,
    )
    distance: Optional[float] = Field(
        default=None,
        description="Maximum allowed distance between the query and result vectors. Lower values corresponds to more similar results. Only one of distance and certainty can be specified.",
    )
    target_vector: Optional[TargetVectorJoinType] = Field(
        default=None,
        description="Specifies vector to use for similarity search when using named vectors.",
    )


class WeaviateKeywordSearchSettingsConfigurationResponse(
    WeaviateSearchCommonSettingsResponse,
):
    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE
    search_kind: Literal[RagSearchKind.KEYWORD_SEARCH] = RagSearchKind.KEYWORD_SEARCH

    minimum_match_or_operator: Optional[int] = Field(
        default=None,
        description="Minimum number of keywords that define a match. Objects returned will have to have at least this many matches.",
    )
    and_operator: Optional[bool] = Field(
        default=None,
        description="Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator",
    )


class WeaviateHybridSearchSettingsConfigurationResponse(
    WeaviateSearchCommonSettingsResponse,
):
    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE
    search_kind: Literal[RagSearchKind.HYBRID_SEARCH] = RagSearchKind.HYBRID_SEARCH

    alpha: float = Field(
        default=0.7,
        description="Balance between the relative weights of the keyword and vector search. 1 is pure vector search, 0 is pure keyword search.",
    )
    query_properties: Optional[list[str]] = Field(
        default=None,
        description="Apply keyword search to only a specified subset of object properties.",
    )
    fusion_type: Optional[HybridFusion] = Field(
        default=None,
        description="Set the fusion algorithm to use. Default is Relative Score Fusion.",
    )
    max_vector_distance: Optional[float] = Field(
        default=None,
        description="Maximum threshold for the vector search component.",
    )
    minimum_match_or_operator: Optional[int] = Field(
        default=None,
        description="Minimum number of keywords that define a match. Objects returned will have to have at least this many matches. Applies to keyword search only.",
    )
    and_operator: Optional[bool] = Field(
        default=None,
        description="Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator. Applies to keyword search only.",
    )
    target_vector: Optional[TargetVectorJoinType] = Field(
        default=None,
        description="Specifies vector to use for vector search when using named vectors.",
    )


RagSearchSettingConfigurationResponseTypes = Union[
    WeaviateHybridSearchSettingsConfigurationResponse,
    WeaviateVectorSimilarityTextSearchSettingsConfigurationResponse,
    WeaviateKeywordSearchSettingsConfigurationResponse,
]


class RagSearchSettingConfigurationVersionResponse(BaseModel):
    setting_configuration_id: UUID = Field(
        description="ID of the parent setting configuration.",
    )
    version_number: int = Field(
        description="Version number of the setting configuration.",
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Optional list of tags configured for this version of the settings configuration.",
    )

    settings: Optional[RagSearchSettingConfigurationResponseTypes] = Field(
        default=None,
        description="Settings configuration for a search request to a RAG provider. None if version has been soft-deleted.",
    )
    created_at: int = Field(
        description="Time the RAG provider settings configuration version was created in unix milliseconds",
    )
    updated_at: int = Field(
        description="Time the RAG provider settings configuration version was updated in unix milliseconds",
    )
    deleted_at: Optional[int] = Field(
        default=None,
        description="Time the RAG provider settings configuration version was soft-deleted in unix milliseconds",
    )


class RagSearchSettingConfigurationResponse(BaseModel):
    id: UUID = Field(description="ID of the setting configuration.")
    task_id: str = Field(description="ID of the parent task.")
    rag_provider_id: Optional[uuid.UUID] = Field(
        default=None,
        description="ID of the rag provider to use with the settings. None if initial rag provider configuration was deleted.",
    )
    name: str = Field(description="Name of the setting configuration.")
    description: Optional[str] = Field(
        default=None,
        description="Description of the setting configuration.",
    )
    latest_version_number: int = Field(
        description="The latest version number of the settings configuration.",
    )
    latest_version: RagSearchSettingConfigurationVersionResponse = Field(
        description="The latest version of the settings configuration.",
    )
    all_possible_tags: Optional[list[str]] = Field(
        default=None,
        description="Set of all tags applied for any version of the settings configuration.",
    )
    created_at: int = Field(
        description="Time the RAG settings configuration was created in unix milliseconds.",
    )
    updated_at: int = Field(
        description="Time the RAG settings configuration was updated in unix milliseconds. Will be updated if a new version of the configuration was created.",
    )


class ListRagSearchSettingConfigurationsResponse(BaseModel):
    count: int = Field(
        description="The total number of RAG search setting configurations matching the parameters.",
    )
    rag_provider_setting_configurations: list[RagSearchSettingConfigurationResponse] = (
        Field(
            description="List of RAG search setting configurations matching the search filters. Length is less than or equal to page_size parameter",
        )
    )


class ListRagSearchSettingConfigurationVersionsResponse(BaseModel):
    count: int = Field(
        description="The total number of RAG search setting configuration versions matching the parameters.",
    )
    rag_provider_setting_configurations: list[
        RagSearchSettingConfigurationVersionResponse
    ] = Field(
        description="List of RAG search setting configuration versions matching the search filters. Length is less than or equal to page_size parameter",
    )


class AgenticPromptMetadataResponse(BaseModel):
    name: str = Field(description="Name of the prompt")
    versions: int = Field(description="Number of versions of the prompt")
    created_at: datetime = Field(description="Timestamp when the prompt was created")


class LLMGetAllMetadataResponse(BaseModel):
    name: str = Field(description="Name of the llm asset")
    versions: int = Field(description="Number of versions of the llm asset")
    created_at: datetime = Field(description="Timestamp when the llm asset was created")
    latest_version_created_at: datetime = Field(
        description="Timestamp when the last version of the llm asset was created",
    )
    deleted_versions: List[int] = Field(
        description="List of deleted versions of the llm asset",
    )


class LLMGetAllMetadataListResponse(BaseModel):
    llm_metadata: list[LLMGetAllMetadataResponse] = Field(
        description="List of llm asset metadata",
    )
    count: int = Field(description="Total number of llm assets matching filters")


class LLMVersionResponse(BaseModel):
    version: int = Field(description="Version number of the llm eval")
    created_at: datetime = Field(
        description="Timestamp when the llm eval version was created",
    )
    deleted_at: Optional[datetime] = Field(
        description="Timestamp when the llm eval version was deleted (None if not deleted)",
    )
    model_provider: ModelProvider = Field(
        description="Model provider chosen for this version of the llm eval",
    )
    model_name: str = Field(
        description="Model name chosen for this version of the llm eval",
    )


class AgenticPromptVersionResponse(LLMVersionResponse):
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


class LLMEvalsVersionListResponse(BaseModel):
    versions: list[LLMVersionResponse] = Field(
        description="List of llm eval version metadata",
    )
    count: int = Field(description="Total number of llm evals matching filters")
