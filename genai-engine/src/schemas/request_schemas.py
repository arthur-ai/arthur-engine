from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from fastapi import HTTPException
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, model_validator
from pydantic_core import Url
from weaviate.classes.query import BM25Operator
from weaviate.collections.classes.grpc import (
    METADATA,
    HybridFusion,
    TargetVectorJoinType,
)
from weaviate.types import INCLUDE_VECTOR

from schemas.enums import (
    DocumentStorageEnvironment,
    ModelProvider,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
    RagProviderEnum,
    RagSearchKind,
    ReasoningEffortEnum,
)
from schemas.llm_schemas import (
    LLMResponseFormat,
    LLMTool,
    LogitBiasItem,
    OpenAIMessage,
    StreamOptions,
    ToolChoice,
    ToolChoiceEnum,
)


class DocumentStorageConfigurationUpdateRequest(BaseModel):
    environment: DocumentStorageEnvironment
    connection_string: Optional[str] = None
    container_name: Optional[str] = None
    bucket_name: Optional[str] = None
    assumable_role_arn: Optional[str] = None

    @model_validator(mode="before")
    def check_azure_or_aws_complete_config(cls, values):
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
    document_storage_configuration: Optional[
        DocumentStorageConfigurationUpdateRequest
    ] = None
    max_llm_rules_per_task_count: Optional[int] = None


class NewDatasetRequest(BaseModel):
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


class DatasetUpdateRequest(BaseModel):
    name: Optional[str] = Field(
        description="Name of the dataset.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the dataset.",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Any metadata to include that describes additional information about the dataset.",
        examples=[{"created_by": "John Doe"}],
    )


class NewDatasetVersionRowColumnItemRequest(BaseModel):
    column_name: str = Field(description="Name of column.")
    column_value: str = Field(description="Value of column for the row.")


class NewDatasetVersionRowRequest(BaseModel):
    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the new dataset row.",
    )


class NewDatasetVersionUpdateRowRequest(BaseModel):
    id: UUID = Field(description="UUID of row to be updated.")
    data: List[NewDatasetVersionRowColumnItemRequest] = Field(
        description="List of column-value pairs in the updated row.",
    )


class NewDatasetVersionRequest(BaseModel):
    rows_to_add: list[NewDatasetVersionRowRequest] = Field(
        description="List of rows to be added to the new dataset version.",
    )
    rows_to_delete: list[UUID] = Field(
        description="List of IDs of rows to be deleted from the new dataset version.",
    )
    rows_to_update: list[NewDatasetVersionUpdateRowRequest] = Field(
        description="List of IDs of rows to be updated in the new dataset version with their new values. "
        "Should include the value in the row for every column in the dataset, not just the updated column values.",
    )


class PutModelProviderCredentials(BaseModel):
    api_key: SecretStr = Field(description="The API key for the provider.")


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
    def check_operators(self):
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
    def check_operators(self):
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
    min_score: int = Field(default=0, description="Minimum score for the llm eval")
    max_score: int = Field(default=1, description="Maximum score for the llm eval")
    config: Optional[LLMRequestConfigSettings] = Field(
        default=None,
        description="LLM configurations for this eval (e.g. temperature, max_tokens, etc.)",
    )


class CreateAgenticPromptRequest(BaseModel):
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

    class Config:
        use_enum_values = True


class VariableTemplateValue(BaseModel):
    name: str = Field(..., description="Name of the variable")
    value: str = Field(..., description="Value of the variable")


class BaseCompletionRequest(BaseModel):
    variables: Optional[List[VariableTemplateValue]] = Field(
        description="List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt",
        default=[],
    )


class PromptCompletionRequest(BaseCompletionRequest):
    """Request schema for running an agentic prompt"""

    stream: Optional[bool] = Field(
        description="Whether to stream the response",
        default=False,
    )
    strict: Optional[bool] = Field(
        description="Whether to enforce strict validation of variables. If True, any variables that are found in the prompt but not in the variables list will raise an error.",
        default=False,
    )

    _variable_map: Dict[str, str] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _build_variable_map(self):
        """Construct a private lookup dictionary for variable substitution"""
        if self.variables:
            self._variable_map = {v.name: v.value for v in self.variables}
        return self


class CompletionRequest(CreateAgenticPromptRequest):
    """Request schema for running an unsaved agentic prompt"""

    completion_request: PromptCompletionRequest = Field(
        default_factory=PromptCompletionRequest,
        description="Run configuration for the unsaved prompt",
    )
