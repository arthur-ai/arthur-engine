from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from arthur_common.models.llm_model_providers import (
    LLMResponseFormat,
    LLMTool,
    LogitBiasItem,
    ModelProvider,
    OpenAIMessage,
    ReasoningEffortEnum,
    StreamOptions,
    ToolChoice,
    ToolChoiceEnum,
)
from arthur_common.models.task_eval_schemas import TraceTransformDefinition
from fastapi import HTTPException, Query
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    model_validator,
)
from pydantic_core import Url
from weaviate.classes.query import BM25Operator
from weaviate.collections.classes.grpc import (
    METADATA,
    HybridFusion,
    TargetVectorJoinType,
)
from weaviate.types import INCLUDE_VECTOR

from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
    NewDatasetVersionUpdateRowRequest,
)
from schemas.enums import (
    DocumentStorageEnvironment,
    EvalType,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
    RagProviderEnum,
    RagSearchKind,
)
from utils.constants import ALLOWED_TRACE_RETENTION_DAYS


class DocumentStorageConfigurationUpdateRequest(BaseModel):
    environment: DocumentStorageEnvironment
    connection_string: Optional[str] = None
    container_name: Optional[str] = None
    bucket_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def check_azure_or_aws_complete_config(
        cls,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        if values.get("environment") == "azure":
            if (values.get("connection_string") is None) or (
                values.get("container_name") is None
            ):
                raise ValueError(
                    "Both connection string and container name must be supplied for Azure document configuration",
                )
        elif values.get("environment") == "aws":
            if values.get("bucket_name") is None:
                raise ValueError(
                    "Bucket name must be supplied for AWS document configuration",
                )
            if values.get("assumable_role_arn") is None:
                raise ValueError(
                    "Role ARN must be supplied for AWS document configuration",
                )
        return values


class ApplicationConfigurationUpdateRequest(BaseModel):
    chat_task_id: Optional[str] = None
    default_currency: Optional[str] = None
    document_storage_configuration: Optional[
        DocumentStorageConfigurationUpdateRequest
    ] = None
    max_llm_rules_per_task_count: Optional[int] = None
    trace_retention_days: Optional[int] = None

    @model_validator(mode="after")
    def validate_trace_retention_days(self) -> "ApplicationConfigurationUpdateRequest":
        if self.trace_retention_days is not None and (
            self.trace_retention_days not in ALLOWED_TRACE_RETENTION_DAYS
        ):
            raise ValueError(
                f"trace_retention_days must be one of {ALLOWED_TRACE_RETENTION_DAYS}",
            )
        return self


class NewDatasetRequest(BaseModel):
    name: str = Field(
        description="Name of the dataset.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the dataset.",
    )
    metadata: Optional[dict[Any, Any]] = Field(
        default=None,
        description="Any metadata to include that describes additional information about the dataset.",
    )


class DatasetUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        description="Name of the dataset.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the dataset.",
    )
    metadata: Optional[dict[Any, Any]] = Field(
        default=None,
        description="Any metadata to include that describes additional information about the dataset.",
        examples=[{"created_by": "John Doe"}],
    )


class NewDatasetVersionRequest(BaseModel):
    rows_to_add: list[NewDatasetVersionRowRequest] = Field(
        description="List of rows to be added to the new dataset version.",
    )
    rows_to_delete: list[UUID] = Field(
        description="List of IDs of rows to be deleted from the new dataset version.",
    )
    rows_to_delete_filter: Optional[list[NewDatasetVersionRowColumnItemRequest]] = (
        Field(
            default=None,
            description="Optional list of column name and value filters. "
            "Rows matching ALL specified column name-value pairs (AND condition) will be deleted from the new dataset version. "
            "This filter is applied in addition to rows_to_delete.",
        )
    )
    rows_to_update: list[NewDatasetVersionUpdateRowRequest] = Field(
        description="List of IDs of rows to be updated in the new dataset version with their new values. "
        "Should include the value in the row for every column in the dataset, not just the updated column values.",
    )


class NewTraceTransformRequest(BaseModel):
    name: str = Field(
        description="Name of the transform.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the transform.",
    )
    definition: TraceTransformDefinition = Field(
        description="Transform definition specifying extraction rules.",
    )


class TraceTransformUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="Name of the transform.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the transform.",
    )
    definition: Optional[TraceTransformDefinition] = Field(
        default=None,
        description="Transform definition specifying extraction rules.",
    )


class GCPServiceAccountCredentialsRequest(BaseModel):
    type: SecretStr
    project_id: SecretStr
    private_key_id: SecretStr
    private_key: SecretStr
    client_email: SecretStr
    client_id: SecretStr
    auth_uri: SecretStr
    token_uri: SecretStr
    auth_provider_x509_cert_url: SecretStr
    client_x509_cert_url: SecretStr
    universe_domain: SecretStr


class PutModelProviderCredentials(BaseModel):
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="The API key for the provider.",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="The vertex AI project ID. Will override the project ID in the key file if provided.",
    )
    region: Optional[str] = Field(
        default=None,
        description="The vertex AI region to use",
    )
    aws_access_key_id: Optional[SecretStr] = Field(
        default=None,
        description="The AWS access key ID.",
    )
    aws_secret_access_key: Optional[SecretStr] = Field(
        default=None,
        description="The AWS secret access key.",
    )
    aws_bedrock_runtime_endpoint: Optional[SecretStr] = Field(
        default=None,
        description="The AWS Bedrock runtime endpoint.",
    )
    aws_role_name: Optional[SecretStr] = Field(
        default=None,
        description="The AWS role name.",
    )
    aws_session_name: Optional[SecretStr] = Field(
        default=None,
        description="The AWS session name.",
    )
    api_base: Optional[SecretStr] = Field(
        default=None,
        description="The API base URL. Used for VLLM models.",
    )
    credentials_file: Optional[GCPServiceAccountCredentialsRequest] = Field(
        default=None,
        description="Optional GCP service account credentials JSON",
    )


class ApiKeyRagAuthenticationConfigRequest(BaseModel):
    authentication_method: Literal[
        RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    ] = RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    api_key: SecretStr = Field(description="API key to use for authentication.")
    host_url: Url = Field(description="URL of host instance to authenticate with.")
    rag_provider: RagAPIKeyAuthenticationProviderEnum = Field(
        description="Name of RAG provider to authenticate with.",
    )


RagAuthenticationConfigRequestTypes = Union[ApiKeyRagAuthenticationConfigRequest]


class RagProviderTestConfigurationRequest(BaseModel):
    authentication_config: RagAuthenticationConfigRequestTypes = Field(
        description="Configuration of the authentication strategy.",
    )


class RagProviderConfigurationRequest(RagProviderTestConfigurationRequest):
    name: str = Field(description="Name of RAG provider configuration.")
    description: Optional[str] = Field(
        default=None,
        description="Description of RAG provider configuration.",
    )


class ApiKeyRagAuthenticationConfigUpdateRequest(BaseModel):
    authentication_method: Literal[
        RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    ] = RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key to use for authentication.",
    )
    host_url: Optional[Url] = Field(
        default=None,
        description="URL of host instance to authenticate with.",
    )
    rag_provider: Optional[RagAPIKeyAuthenticationProviderEnum] = Field(
        default=None,
        description="Name of RAG provider to authenticate with.",
    )


RagAuthenticationConfigUpdateRequestTypes = Union[
    ApiKeyRagAuthenticationConfigUpdateRequest
]


class RagProviderConfigurationUpdateRequest(BaseModel):
    authentication_config: Optional[RagAuthenticationConfigUpdateRequestTypes] = Field(
        default=None,
        description="Configuration of the authentication strategy.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Name of RAG provider configuration.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of RAG provider configuration.",
    )


class WeaviateSearchCommonSettingsRequest(BaseModel):
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


class WeaviateVectorSimilarityTextSearchSettingsBaseConfigurationRequest(
    WeaviateSearchCommonSettingsRequest,
):
    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE

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


class WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest(
    WeaviateVectorSimilarityTextSearchSettingsBaseConfigurationRequest,
):
    search_kind: Literal[RagSearchKind.VECTOR_SIMILARITY_TEXT_SEARCH] = (
        RagSearchKind.VECTOR_SIMILARITY_TEXT_SEARCH
    )

    def to_client_request_model(
        self,
        query_text: str,
    ) -> "RagVectorSimilarityTextSearchSettingRequest":
        return RagVectorSimilarityTextSearchSettingRequest(
            settings=WeaviateVectorSimilarityTextSearchSettingsRequest(
                collection_name=self.collection_name,
                query=query_text,
                limit=self.limit,
                certainty=self.certainty,
                return_properties=self.return_properties,
                include_vector=self.include_vector,
                return_metadata=self.return_metadata,
                distance=self.distance,
                target_vector=self.target_vector,
                offset=self.offset,
                auto_limit=self.auto_limit,
            ),
        )


class WeaviateVectorSimilarityTextSearchSettingsRequest(
    WeaviateVectorSimilarityTextSearchSettingsBaseConfigurationRequest,
):
    # fields match the names of the inputs to the weaviate near_text function
    # the only exception is collection_name, which is used to fetch the vector collection used for the similarity search
    # https://weaviate-python-client.readthedocs.io/en/latest/weaviate.collections.grpc.html#weaviate.collections.grpc.query._QueryGRPC.near_text
    # left out for now: group_by, rerank, filters, move_to, move_away, include_references
    query: Union[List[str], str] = Field(
        description="Input text to find objects with near vectors for.",
    )

    def _to_client_settings_dict(self) -> dict[str, Any]:
        """Parses settings to the client parameters for the near_text function."""
        return self.model_dump(
            exclude={"collection_name", "rag_provider"},
        )


RagVectorSimilarityTextSearchSettingRequestTypes = Union[
    WeaviateVectorSimilarityTextSearchSettingsRequest
]


class RagVectorSimilarityTextSearchSettingRequest(BaseModel):
    settings: RagVectorSimilarityTextSearchSettingRequestTypes = Field(
        description="Settings for the similarity text search request to the vector database.",
    )


class WeaviateKeywordSearchSettingsBaseConfigurationRequest(
    WeaviateSearchCommonSettingsRequest,
):
    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE

    minimum_match_or_operator: Optional[int] = Field(
        default=None,
        description="Minimum number of keywords that define a match. Objects returned will have to have at least this many matches.",
    )
    and_operator: Optional[bool] = Field(
        default=None,
        description="Search returns objects that contain all tokens in the search string. Cannot be used with minimum_match_or_operator",
    )

    @model_validator(mode="after")
    def check_operators(
        self,
    ) -> "WeaviateKeywordSearchSettingsBaseConfigurationRequest":
        if self.and_operator and self.minimum_match_or_operator:
            raise HTTPException(
                status_code=400,
                detail="Both and_operator and minimum_match_or_operator cannot be set. The search must either use the or operator (default) or the and operator.",
                headers={"full_stacktrace": "false"},
            )

        return self


class WeaviateKeywordSearchSettingsConfigurationRequest(
    WeaviateKeywordSearchSettingsBaseConfigurationRequest,
):
    search_kind: Literal[RagSearchKind.KEYWORD_SEARCH] = RagSearchKind.KEYWORD_SEARCH

    def to_client_request_model(
        self,
        query_text: str,
    ) -> "RagKeywordSearchSettingRequest":
        return RagKeywordSearchSettingRequest(
            settings=WeaviateKeywordSearchSettingsRequest(
                collection_name=self.collection_name,
                query=query_text,
                limit=self.limit,
                return_properties=self.return_properties,
                include_vector=self.include_vector,
                return_metadata=self.return_metadata,
                minimum_match_or_operator=self.minimum_match_or_operator,
                and_operator=self.and_operator,
                offset=self.offset,
                auto_limit=self.auto_limit,
            ),
        )


class WeaviateKeywordSearchSettingsRequest(
    WeaviateKeywordSearchSettingsBaseConfigurationRequest,
):
    # fields match the names of the inputs to the weaviate bm25 function
    # https://weaviate-python-client.readthedocs.io/en/stable/weaviate-agents-python-client/docs/weaviate_agents.personalization.classes.html#weaviate_agents.personalization.classes.BM25QueryParameters
    # left out filters, rerank, return_references, group_by
    query: str = Field(
        description="Input text to find objects with keyword matches.",
    )

    def _to_client_settings_dict(self) -> dict[str, Any]:
        """Parses settings to the client parameters for the bm25 function."""
        settings_dict = self.model_dump(
            exclude={
                "collection_name",
                "rag_provider",
                "minimum_match_or_operator",
                "and_operator",
            },
        )

        if self.and_operator:
            settings_dict["operator"] = BM25Operator.and_()
        elif self.minimum_match_or_operator is not None:
            settings_dict["operator"] = BM25Operator.or_(
                minimum_match=self.minimum_match_or_operator,
            )

        return settings_dict


RagKeywordSearchSettingRequestTypes = Union[WeaviateKeywordSearchSettingsRequest]


class RagKeywordSearchSettingRequest(BaseModel):
    settings: RagKeywordSearchSettingRequestTypes = Field(
        description="Settings for the keyword search request to the vector database.",
    )


class WeaviateHybridSearchSettingsBaseRequest(
    WeaviateSearchCommonSettingsRequest,
):
    rag_provider: Literal[RagProviderEnum.WEAVIATE] = RagProviderEnum.WEAVIATE

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

    @model_validator(mode="after")
    def check_operators(self) -> "WeaviateHybridSearchSettingsBaseRequest":
        if self.and_operator and self.minimum_match_or_operator:
            raise HTTPException(
                status_code=400,
                detail="Both and_operator and minimum_match_or_operator cannot be set. The search must either use the or operator (default) or the and operator.",
                headers={"full_stacktrace": "false"},
            )

        return self


class WeaviateHybridSearchSettingsConfigurationRequest(
    WeaviateHybridSearchSettingsBaseRequest,
):
    search_kind: Literal[RagSearchKind.HYBRID_SEARCH] = RagSearchKind.HYBRID_SEARCH

    def to_client_request_model(
        self,
        query_text: str,
    ) -> "RagHybridSearchSettingRequest":
        return RagHybridSearchSettingRequest(
            settings=WeaviateHybridSearchSettingsRequest(
                collection_name=self.collection_name,
                query=query_text,
                limit=self.limit,
                alpha=self.alpha,
                query_properties=self.query_properties,
                fusion_type=self.fusion_type,
                max_vector_distance=self.max_vector_distance,
                minimum_match_or_operator=self.minimum_match_or_operator,
                and_operator=self.and_operator,
                target_vector=self.target_vector,
                include_vector=self.include_vector,
                offset=self.offset,
                auto_limit=self.auto_limit,
                return_metadata=self.return_metadata,
                return_properties=self.return_properties,
            ),
        )


class WeaviateHybridSearchSettingsRequest(
    WeaviateHybridSearchSettingsBaseRequest,
):
    # fields match the names of the inputs to the weaviate hybrid function
    # some are left out for now: return_references, group_by, rerank, filters, vector, target_vector
    query: str = Field(
        description="Input text to find objects with near vectors or keyword matches.",
    )

    def _to_client_settings_dict(self) -> dict[str, Any]:
        """Parses settings to the client parameters for the hybrid function."""
        settings_dict = self.model_dump(
            exclude={
                "collection_name",
                "rag_provider",
                "minimum_match_or_operator",
                "and_operator",
            },
        )

        if self.and_operator:
            settings_dict["operator"] = BM25Operator.and_()
        elif self.minimum_match_or_operator is not None:
            settings_dict["operator"] = BM25Operator.or_(
                minimum_match=self.minimum_match_or_operator,
            )

        return settings_dict


RagHybridSearchSettingRequestTypes = Union[WeaviateHybridSearchSettingsRequest]


class RagHybridSearchSettingRequest(BaseModel):
    settings: RagHybridSearchSettingRequestTypes = Field(
        description="Settings for the hybrid search request to the vector database.",
    )


RagSearchSettingConfigurationRequestTypes = Union[
    WeaviateHybridSearchSettingsConfigurationRequest,
    WeaviateKeywordSearchSettingsConfigurationRequest,
    WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
]


class RagSearchSettingConfigurationRequest(BaseModel):
    settings: RagSearchSettingConfigurationRequestTypes = Field(
        description="Settings configuration for a search request to a RAG provider.",
    )
    rag_provider_id: UUID = Field(
        description="ID of the rag provider to use with the settings.",
    )
    name: str = Field(description="Name of the search setting configuration.")
    description: Optional[str] = Field(
        default=None,
        description="Description of the search setting configuration.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tags to configure for this version of the search settings configuration.",
    )


class RagSearchSettingConfigurationUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="Name of the setting configuration.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the setting configuration.",
    )
    rag_provider_id: Optional[UUID] = Field(
        default=None,
        description="ID of the rag provider configuration to use the settings with.",
    )


class RagSearchSettingConfigurationNewVersionRequest(BaseModel):
    settings: RagSearchSettingConfigurationRequestTypes = Field(
        description="Settings configuration for a search request to a RAG provider.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tags to configure for this version of the search settings configuration.",
    )


class RagSearchSettingConfigurationVersionUpdateRequest(BaseModel):
    tags: list[str] = Field(
        description="List of tags to update this version of the search settings configuration with.",
    )


class LLMGetVersionsFilterRequest(BaseModel):
    """Request schema for filtering agentic prompts and llm evals with comprehensive filtering options."""

    # Optional filters
    model_provider: Optional[ModelProvider] = Field(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    )
    model_name: Optional[str] = Field(
        None,
        description="Filter by model name using partial matching (e.g., 'gpt-4', 'claude'). Supports SQL LIKE pattern matching with % wildcards.",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    exclude_deleted: Optional[bool] = Field(
        False,
        description="Whether to exclude deleted prompt versions from the results. Default is False.",
    )
    min_version: Optional[int] = Field(
        None,
        ge=1,
        description="Minimum version number to filter on (inclusive).",
    )
    max_version: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum version number to filter on (inclusive).",
    )


class LLMGetAllFilterRequest(BaseModel):
    """Request schema for filtering agentic prompts and llm evals with comprehensive filtering options."""

    # Optional filters
    llm_asset_names: Optional[list[str]] = Field(
        None,
        description="LLM asset names to filter on using partial matching. If provided, llm assets matching any of these name patterns will be returned",
    )
    model_provider: Optional[ModelProvider] = Field(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    )
    model_name: Optional[str] = Field(
        None,
        description="Filter by model name using partial matching (e.g., 'gpt-4o', 'claude-3-5-sonnet').",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    tags: Optional[list[Annotated[str, Field(max_length=200)]]] = Field(
        None,
        description="List of tags to filter for items that have any matching tag across any version.",
        max_length=50,
    )


class LLMRequestConfigSettings(BaseModel):
    timeout: Optional[float] = Field(None, description="Request timeout in seconds")
    temperature: Optional[float] = Field(
        None,
        description="Sampling temperature (0.0 to 2.0). Higher values make output more random",
    )
    top_p: Optional[float] = Field(
        None,
        description="Top-p sampling parameter (0.0 to 1.0). Alternative to temperature",
    )
    max_tokens: Optional[int] = Field(
        None,
        description="Maximum number of tokens to generate in the response",
    )
    stop: Optional[str] = Field(
        None,
        description="Stop sequence(s) where the model should stop generating",
    )
    presence_penalty: Optional[float] = Field(
        None,
        description="Presence penalty (-2.0 to 2.0). Positive values penalize new tokens based on their presence",
    )
    frequency_penalty: Optional[float] = Field(
        None,
        description="Frequency penalty (-2.0 to 2.0). Positive values penalize tokens based on frequency",
    )
    seed: Optional[int] = Field(
        None,
        description="Random seed for reproducible outputs",
    )
    logprobs: Optional[bool] = Field(
        None,
        description="Whether to return log probabilities of output tokens",
    )
    top_logprobs: Optional[int] = Field(
        None,
        description="Number of most likely tokens to return log probabilities for (1-20)",
    )
    logit_bias: Optional[List[LogitBiasItem]] = Field(
        None,
        description="Modify likelihood of specified tokens appearing in completion",
    )
    max_completion_tokens: Optional[int] = Field(
        None,
        description="Maximum number of completion tokens (alternative to max_tokens)",
    )
    reasoning_effort: Optional[ReasoningEffortEnum] = Field(
        None,
        description="Reasoning effort level for models that support it (e.g., OpenAI o1 series)",
    )
    thinking: Optional[AnthropicThinkingParam] = Field(
        None,
        description="Anthropic-specific thinking parameter for Claude models",
    )


class LLMPromptRequestConfigSettings(LLMRequestConfigSettings):
    response_format: Optional[LLMResponseFormat] = Field(
        None,
        description="Response format specification (e.g., {'type': 'json_object'} for JSON mode)",
    )
    tool_choice: Optional[Union[ToolChoiceEnum, ToolChoice]] = Field(
        None,
        description="Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)",
    )
    stream_options: Optional[StreamOptions] = Field(
        None,
        description="Additional streaming configuration options",
    )


class CreateEvalRequest(BaseModel):
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: ModelProvider = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure')",
    )
    instructions: str = Field(description="Instructions for the llm eval")
    config: Optional[LLMRequestConfigSettings] = Field(
        default=None,
        description="LLM configurations for this eval (e.g. temperature, max_tokens, etc.)",
    )


class PIIEvalConfig(BaseModel):
    """Configuration for PII detection evals."""

    disabled_pii_entities: Optional[List[str]] = Field(
        default=None,
        description="List of PII entity types to disable (e.g. ['EMAIL_ADDRESS', 'PHONE_NUMBER'])",
    )
    pii_confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score for a PII entity to be flagged",
    )
    allow_list: Optional[List[str]] = Field(
        default=None,
        description="List of values that should not be flagged as PII",
    )


class ToxicityEvalConfig(BaseModel):
    """Configuration for toxicity detection evals."""

    toxicity_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum toxicity score for text to be flagged",
    )


class PromptInjectionEvalConfig(BaseModel):
    """Configuration for prompt injection detection evals."""


# Map from EvalType to its typed config model for validation.
# Config is stored as a raw dict in the DB; these models define the valid fields.
_ML_EVAL_CONFIG_MODELS: Dict[EvalType, type] = {
    EvalType.PII: PIIEvalConfig,
    EvalType.PII_V1: PIIEvalConfig,
    EvalType.TOXICITY: ToxicityEvalConfig,
    EvalType.PROMPT_INJECTION: PromptInjectionEvalConfig,
}


class CreateMLEvalRequest(BaseModel):
    eval_type: EvalType = Field(
        description="Type of ML eval (e.g. 'pii', 'toxicity', 'prompt_injection')",
    )
    # Config is a free-form dict whose valid fields are defined by the typed models above
    # (PIIEvalConfig, ToxicityEvalConfig, PromptInjectionEvalConfig).
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional configuration for the ML eval. Valid fields depend on eval_type.",
    )

    @model_validator(mode="after")
    def validate_ml_eval_type(self) -> "CreateMLEvalRequest":
        ml_eval_types = {
            EvalType.PII,
            EvalType.PII_V1,
            EvalType.TOXICITY,
            EvalType.PROMPT_INJECTION,
        }
        if self.eval_type not in ml_eval_types:
            raise ValueError(
                f"eval_type must be one of {[e.value for e in ml_eval_types]}, got '{self.eval_type}'",
            )
        return self


class CreateAnyEvalRequest(BaseModel):
    """Unified eval creation request used by the v2 /evals endpoints.

    For llm_as_a_judge evals model_name, model_provider and instructions are required.
    For ML evals (pii, toxicity, prompt_injection) only eval_type (and optionally config)
    are needed. Valid config fields per eval_type are documented in PIIEvalConfig,
    ToxicityEvalConfig, and PromptInjectionEvalConfig.
    """

    eval_type: EvalType = Field(
        description="Type of eval: 'llm_as_a_judge', 'pii', 'pii_v1', 'toxicity', 'prompt_injection'",
    )
    model_name: Optional[str] = Field(
        default=None,
        description="LLM model name — required for llm_as_a_judge evals",
    )
    model_provider: Optional[ModelProvider] = Field(
        default=None,
        description="LLM model provider — required for llm_as_a_judge evals",
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Eval instructions — required for llm_as_a_judge evals",
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional configuration. For llm_as_a_judge: LLM settings (temperature, etc.). "
            "For ML evals: see PIIEvalConfig, ToxicityEvalConfig, PromptInjectionEvalConfig."
        ),
    )

    @model_validator(mode="after")
    def validate_for_type(self) -> "CreateAnyEvalRequest":
        if self.eval_type == EvalType.LLM_AS_A_JUDGE:
            if not self.model_name:
                raise ValueError("model_name is required for llm_as_a_judge evals")
            if not self.model_provider:
                raise ValueError("model_provider is required for llm_as_a_judge evals")
            if not self.instructions:
                raise ValueError("instructions is required for llm_as_a_judge evals")
        return self


class CreateAgenticPromptRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    messages: List[OpenAIMessage] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: ModelProvider = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure')",
    )
    tools: Optional[List[LLMTool]] = Field(
        None,
        description="Available tools/functions for the model to call, in OpenAI function calling format",
    )
    config: Optional[LLMPromptRequestConfigSettings] = Field(
        None,
        description="LLM configurations for this prompt (e.g. temperature, max_tokens, etc.)",
    )


class BaseCompletionRequest(BaseModel):
    variables: Optional[List[VariableTemplateValue]] = Field(
        description="List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt",
        default=[],
    )

    _variable_map: Dict[str, str] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _build_variable_map(self) -> "BaseCompletionRequest":
        """Construct a private lookup dictionary for variable substitution"""
        if self.variables:
            self._variable_map = {v.name: v.value for v in self.variables}
        return self


class VariableRenderingRequest(BaseCompletionRequest):
    strict: Optional[bool] = Field(
        description="Whether to enforce strict validation of variables. If True, any variables that are found in the prompt but not in the variables list will raise an error.",
        default=False,
    )


class PromptCompletionRequest(VariableRenderingRequest):
    """Request schema for running an agentic prompt"""

    stream: Optional[bool] = Field(
        description="Whether to stream the response",
        default=False,
    )


class CompletionRequest(CreateAgenticPromptRequest):
    """Request schema for running an unsaved agentic prompt"""

    completion_request: PromptCompletionRequest = Field(
        default_factory=PromptCompletionRequest,
        description="Run configuration for the unsaved prompt",
    )


class SavedPromptRenderingRequest(BaseModel):
    """Request schema for rendering an unsaved agentic prompt with variables"""

    completion_request: VariableRenderingRequest = Field(
        default_factory=VariableRenderingRequest,
        description="Rendering configuration for the unsaved prompt",
    )


class UnsavedPromptRenderingRequest(SavedPromptRenderingRequest):
    """Request schema for rendering an unsaved agentic prompt with variables"""

    messages: List[OpenAIMessage] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )


class UnsavedPromptVariablesRequest(BaseModel):
    """Request schema for getting the list of variables needed from an unsaved prompt's messages"""

    messages: List[OpenAIMessage] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )


class AgenticAnnotationRequest(BaseModel):
    annotation_score: int = Field(
        ...,
        ge=0,
        le=1,
        description="Binary score for whether a traces has been liked or disliked (0 = disliked, 1 = liked)",
    )
    annotation_description: Optional[str] = Field(
        default=None,
        description="Description of the annotation",
    )


class TransformListFilterRequest(BaseModel):
    """Request schema for filtering transforms with comprehensive filtering options."""

    name: Optional[str] = Field(
        None,
        description="Name of the transform to filter on using partial matching.",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )


class CreateTestRunRequest(BaseModel):
    """Request schema for creating a continuous eval test run"""

    trace_ids: List[str] = Field(
        description="List of trace IDs to test the continuous eval against",
        min_length=1,
        max_length=50,
    )


class ContinuousEvalTransformVariableMappingRequest(BaseModel):
    transform_variable: str = Field(description="Name of the transform variable")
    eval_variable: str = Field(description="Name of the eval variable")


class ContinuousEvalCreateRequest(BaseModel):
    """Request schema for creating a continuous eval"""

    name: str = Field(description="Name of the continuous eval")
    description: Optional[str] = Field(
        default=None,
        description="Description of the continuous eval",
    )
    eval_type: Literal["llm_eval", "ml_eval"] = Field(
        default="llm_eval",
        description="Type of evaluator: 'llm_eval' or 'ml_eval'.",
    )
    llm_eval_name: Optional[str] = Field(
        default=None,
        description="Name of the eval to create the continuous eval for",
    )
    llm_eval_version: Optional[Union[str, int]] = Field(
        default=None,
        description="Version of the eval. Can be 'latest', a version number, an ISO datetime string, or a tag.",
    )
    transform_id: UUID = Field(
        description="ID of the transform to create the continuous eval for",
    )
    transform_variable_mapping: List[ContinuousEvalTransformVariableMappingRequest] = (
        Field(
            description="Mapping of transform variables to eval variables.",
        )
    )
    enabled: bool = Field(
        default=True,
        description="Whether to enable or disable a continuous eval. Defaults to True.",
    )

    @model_validator(mode="after")
    def validate_eval_ref(self) -> "ContinuousEvalCreateRequest":
        if not self.llm_eval_name:
            raise ValueError("llm_eval_name is required")
        return self


class UpdateContinuousEvalRequest(BaseModel):
    """Request schema for creating a continuous eval"""

    name: Optional[str] = Field(default=None, description="Name of the continuous eval")
    description: Optional[str] = Field(
        default=None,
        description="Description of the continuous eval",
    )
    llm_eval_name: Optional[str] = Field(
        default=None,
        description="Name of the llm eval to create the continuous eval for",
    )
    llm_eval_version: Optional[Union[str, int]] = Field(
        default=None,
        description="Version of the llm eval to create the continuous eval for. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
    )
    transform_id: Optional[UUID] = Field(
        default=None,
        description="ID of the transform to create the continuous eval for",
    )
    transform_variable_mapping: Optional[
        List[ContinuousEvalTransformVariableMappingRequest]
    ] = Field(
        default=None,
        description="Mapping of transform variables to eval variables.",
    )
    enabled: Optional[bool] = Field(
        default=None,
        description="Whether to enable or disable a continuous eval.",
    )

    @model_validator(mode="after")
    def validate_request(self) -> "UpdateContinuousEvalRequest":
        if self.llm_eval_name is not None and self.llm_eval_version is None:
            raise ValueError(
                "Must specify which version of the llm eval this continuous eval should be associated with",
            )
        if self.transform_variable_mapping is None:
            if (
                self.transform_id is not None
                or self.llm_eval_name is not None
                or self.llm_eval_version is not None
            ):
                raise ValueError(
                    "Must also update the transform variable mapping if updating the transform or llm eval",
                )
        return self


class ContinuousEvalListFilterRequest(BaseModel):
    """Request schema for filtering continuous evals with comprehensive filtering options."""

    # Optional filters
    name: Optional[str] = Field(
        None,
        description="Name of the continuous eval to filter on",
    )
    llm_eval_name: Optional[str] = Field(
        None,
        description="LLM eval name to filter on",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    enabled: Optional[bool] = Field(
        None,
        description="Whether the continuous eval is enabled.",
    )
    continuous_eval_ids: Optional[List[UUID]] = Field(
        None,
        description="List of continuous eval IDs to filter on",
    )
    llm_eval_name_exact: Optional[str] = Field(
        None,
        description="Exact LLM eval name to filter on (case-sensitive exact match)",
    )
    llm_eval_version: Optional[int] = Field(
        None,
        description="LLM eval version to filter on",
    )

    @staticmethod
    def from_query_parameters(
        name: Optional[str] = Query(
            None,
            description="Name of the continuous eval to filter on.",
        ),
        llm_eval_name: Optional[str] = Query(
            None,
            description="Name of the llm eval to filter on",
        ),
        created_after: Optional[str] = Query(
            None,
            description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
        ),
        created_before: Optional[str] = Query(
            None,
            description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
        ),
        enabled: Optional[str] = Query(
            None,
            description="Whether the continuous eval is enabled.",
        ),
        continuous_eval_ids: Optional[List[str]] = Query(
            None,
            description="List of continuous eval IDs to filter on.",
        ),
        llm_eval_name_exact: Optional[str] = Query(
            None,
            description="Exact LLM eval name to filter on (case-sensitive exact match).",
        ),
        llm_eval_version: Optional[int] = Query(
            None,
            description="LLM eval version to filter on.",
        ),
    ) -> "ContinuousEvalListFilterRequest":
        """Create a ContinuousEvalListFilterRequest from query parameters."""
        parsed_continuous_eval_ids = None
        if continuous_eval_ids:
            try:
                parsed_continuous_eval_ids = [UUID(id) for id in continuous_eval_ids]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid UUID format for parameter 'continuous_eval_ids': {e}",
                )

        return ContinuousEvalListFilterRequest(
            name=name,
            llm_eval_name=llm_eval_name,
            created_after=(
                datetime.fromisoformat(created_after) if created_after else None
            ),
            created_before=(
                datetime.fromisoformat(created_before) if created_before else None
            ),
            enabled=enabled.lower() == "true" if enabled else None,
            continuous_eval_ids=parsed_continuous_eval_ids,
            llm_eval_name_exact=llm_eval_name_exact,
            llm_eval_version=llm_eval_version,
        )


class ContinuousEvalRunResultsListFilterRequest(BaseModel):
    """Request schema for filtering continuous eval run results"""

    # Optional filters
    ids: Optional[List[UUID]] = Field(
        None,
        description="List of agentic annotation IDs to filter on",
    )
    continuous_eval_ids: Optional[List[UUID]] = Field(
        None,
        description="List of continuous eval IDs to filter on",
    )
    eval_name: Optional[str] = Field(
        None,
        description="Name of the continuous eval to filter on",
    )
    trace_ids: Optional[List[str]] = Field(
        None,
        description="List of trace IDs to filter on",
    )
    annotation_score: Optional[int] = Field(
        None,
        description="Annotation score to filter on",
    )
    run_status: Optional[ContinuousEvalRunStatus] = Field(
        None,
        description="Run status to filter on",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    continuous_eval_enabled: Optional[bool] = Field(
        None,
        description="Whether the continuous eval is enabled.",
    )

    @staticmethod
    def from_query_parameters(
        ids: Optional[List[str]] = Query(
            None,
            description="List of agentic annotation IDs to filter on.",
        ),
        continuous_eval_ids: Optional[List[str]] = Query(
            None,
            description="List of continuous eval IDs to filter on.",
        ),
        eval_name: Optional[str] = Query(
            None,
            description="Name of the continuous eval to filter on.",
        ),
        trace_ids: Optional[List[str]] = Query(
            None,
            description="List of trace IDs to filter on.",
        ),
        annotation_score: Optional[int] = Query(
            None,
            description="Annotation score to filter on.",
        ),
        run_status: Optional[ContinuousEvalRunStatus] = Query(
            None,
            description="Run status to filter on.",
        ),
        created_after: Optional[str] = Query(
            None,
            description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
        ),
        created_before: Optional[str] = Query(
            None,
            description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
        ),
        continuous_eval_enabled: Optional[str] = Query(
            None,
            description="Whether the continuous eval is enabled.",
        ),
    ) -> "ContinuousEvalRunResultsListFilterRequest":
        """Create a ContinuousEvalRunResultsListFilterRequest from query parameters."""
        # Validate UUID parameters
        parsed_ids = None
        if ids:
            try:
                parsed_ids = [UUID(i) for i in ids]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid UUID format for parameter 'ids': {e}",
                )

        parsed_continuous_eval_ids = None
        if continuous_eval_ids:
            try:
                parsed_continuous_eval_ids = [UUID(i) for i in continuous_eval_ids]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid UUID format for parameter 'continuous_eval_ids': {e}",
                )

        return ContinuousEvalRunResultsListFilterRequest(
            ids=parsed_ids,
            continuous_eval_ids=parsed_continuous_eval_ids,
            eval_name=eval_name,
            trace_ids=trace_ids,
            annotation_score=annotation_score,
            run_status=run_status,
            created_after=(
                datetime.fromisoformat(created_after) if created_after else None
            ),
            created_before=(
                datetime.fromisoformat(created_before) if created_before else None
            ),
            continuous_eval_enabled=(
                continuous_eval_enabled.lower() == "true"
                if continuous_eval_enabled
                else None
            ),
        )


class AgenticAnnotationListFilterRequest(BaseModel):
    """Request schema for filtering annotations"""

    # Optional filters
    continuous_eval_id: Optional[UUID] = Field(
        None,
        description="ID of the continuous eval to filter on",
    )
    annotation_type: Optional[AgenticAnnotationType] = Field(
        None,
        description="Annotation type to filter on",
    )
    annotation_score: Optional[int] = Field(
        None,
        description="Annotation score to filter on",
    )
    run_status: Optional[ContinuousEvalRunStatus] = Field(
        None,
        description="Run status to filter on",
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    )

    @staticmethod
    def from_query_parameters(
        continuous_eval_id: Optional[str] = Query(
            None,
            description="ID of the continuous eval to filter on.",
        ),
        annotation_type: Optional[str] = Query(
            None,
            description="Annotation type to filter on.",
        ),
        annotation_score: Optional[int] = Query(
            None,
            description="Annotation score to filter on.",
        ),
        run_status: Optional[ContinuousEvalRunStatus] = Query(
            None,
            description="Run status to filter on.",
        ),
        created_after: Optional[str] = Query(
            None,
            description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
        ),
        created_before: Optional[str] = Query(
            None,
            description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
        ),
    ) -> "AgenticAnnotationListFilterRequest":
        """Create a AgenticAnnotationListFilterRequest from query parameters."""
        return AgenticAnnotationListFilterRequest(
            continuous_eval_id=UUID(continuous_eval_id) if continuous_eval_id else None,
            annotation_type=(
                AgenticAnnotationType(annotation_type) if annotation_type else None
            ),
            annotation_score=annotation_score,
            run_status=run_status,
            created_after=(
                datetime.fromisoformat(created_after) if created_after else None
            ),
            created_before=(
                datetime.fromisoformat(created_before) if created_before else None
            ),
        )


# ============================================================================
# Synthetic Data Generation Schemas
# ============================================================================


class SyntheticDataColumnDescription(BaseModel):
    """Description of a column for synthetic data generation."""

    column_name: str = Field(
        description="Name of the column to generate data for.",
    )
    description: str = Field(
        description="Description of what this column contains and how to generate realistic values.",
    )


class SyntheticDataGenerationRequest(BaseModel):
    """Request for initial synthetic data generation."""

    dataset_purpose: str = Field(
        description="Description of the dataset's purpose and what the data represents.",
    )
    column_descriptions: List[SyntheticDataColumnDescription] = Field(
        description="Descriptions for each column to guide generation.",
    )
    num_rows: int = Field(
        default=10,
        ge=1,
        le=25,
        description="Number of rows to generate (1-25).",
    )
    model_provider: ModelProvider = Field(
        description="Provider of the LLM model to use for generation.",
    )
    model_name: str = Field(
        description="Name of the LLM model to use for generation.",
    )
    config: Optional[LLMRequestConfigSettings] = Field(
        default=None,
        description="Optional LLM configuration settings (temperature, max_tokens, etc.).",
    )


class SyntheticDataConversationRequest(BaseModel):
    """Request for continuing a synthetic data generation conversation."""

    message: str = Field(
        description="User's message/instruction for refining the generated data.",
    )
    current_rows: List[NewDatasetVersionRowRequest] = Field(
        description="Current state of generated rows (including any manual edits).",
    )
    conversation_history: List[OpenAIMessage] = Field(
        description="Previous conversation messages for context.",
    )
    dataset_purpose: str = Field(
        description="Original dataset purpose for context.",
    )
    column_descriptions: List[SyntheticDataColumnDescription] = Field(
        description="Original column descriptions for context.",
    )
    model_provider: ModelProvider = Field(
        description="Provider of the LLM model to use for generation.",
    )
    model_name: str = Field(
        description="Name of the LLM model to use for generation.",
    )
    config: Optional[LLMRequestConfigSettings] = Field(
        default=None,
        description="Optional LLM configuration settings (temperature, max_tokens, etc.).",
    )
