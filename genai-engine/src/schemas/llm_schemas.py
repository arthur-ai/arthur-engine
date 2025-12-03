import warnings
from typing import List, Optional, Type, Union

from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import BaseModel, Field, field_validator, model_validator

from schemas.common_schemas import JsonSchema
from schemas.enums import (
    LLMResponseFormatEnum,
    MessageRole,
    OpenAIMessageType,
    ReasoningEffortEnum,
    ToolChoiceEnum,
)

warnings.filterwarnings(
    "ignore",
    message='Field name "schema".*shadows an attribute in parent "BaseModel"',
    category=UserWarning,
)


class StreamOptions(BaseModel):
    include_usage: Optional[bool] = Field(
        None,
        description="Whether to include usage information in the stream",
    )


class LogitBiasItem(BaseModel):
    token_id: int = Field(..., description="Token ID to bias")
    bias: float = Field(
        ...,
        ge=-100,
        le=100,
        description="Bias value between -100 and 100",
    )


class ToolCallFunction(BaseModel):
    name: str = Field(..., description="Name of the function to call")
    arguments: str = Field(..., description="JSON string of function arguments")


class ToolCall(BaseModel):
    type: str = Field(
        default="function",
        description="The type of tool call. Currently the only type supported is 'function'.",
    )
    id: str = Field(..., description="Unique identifier for the tool call")
    function: ToolCallFunction = Field(..., description="Function details")

    @field_validator("type", mode="before")
    @classmethod
    def force_type(cls, v):
        return "function"


class ImageURL(BaseModel):
    url: str = Field(..., description="URL of the image")


class InputAudio(BaseModel):
    data: str = Field(..., description="Base64 encoded audio data")
    format: str = Field(
        ...,
        description="audio format (e.g. 'mp3', 'wav', 'flac', etc.)",
    )


class OpenAIMessageItem(BaseModel):
    type: OpenAIMessageType = Field(
        ...,
        description="Type of the message (either 'text', 'image_url', or 'input_audio')",
    )
    text: Optional[str] = Field(
        default=None,
        description="Text content of the message if type is 'text'",
    )
    image_url: Optional[ImageURL] = Field(
        default=None,
        description="Image URL content of the message if type is 'image_url'",
    )
    input_audio: Optional[InputAudio] = Field(
        default=None,
        description="Input audio content of the message if type is 'input_audio'",
    )

    class Config:
        use_enum_values = True


class OpenAIMessage(BaseModel):
    """
    The message schema class for the prompts playground.
    This class adheres to OpenAI's message schema.
    """

    role: MessageRole = Field(description="Role of the message")
    name: Optional[str] = Field(
        default=None,
        description="An optional name for the participant. Provides the model information to differentiate between participants of the same role.",
    )
    content: Optional[str | List[OpenAIMessageItem]] = Field(
        default=None,
        description="Content of the message",
    )
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None,
        description="Tool calls made by assistant",
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        description="ID of the tool call this message is responding to",
    )

    class Config:
        use_enum_values = True


class ToolFunction(BaseModel):
    name: str = Field(..., description="The name of the tool/function")
    description: Optional[str] = Field(
        default=None,
        description="Description of what the tool does",
    )
    parameters: Optional[JsonSchema] = Field(
        default=None,
        description="The function's parameter schema",
    )


class LLMTool(BaseModel):
    type: str = Field(
        default="function",
        description="The type of tool. Should always be 'function'",
    )
    function: ToolFunction = Field(..., description="The function definition")
    strict: Optional[bool] = Field(
        default=None,
        description="Whether the function definition should use OpenAI's strict mode",
    )

    @field_validator("type", mode="before")
    @classmethod
    def force_type(cls, v):
        return "function"


class LLMResponseSchema(BaseModel):
    name: str = Field(..., description="Name of the schema")
    description: Optional[str] = Field(None, description="Description of the schema")
    schema: JsonSchema = Field(..., description="The JSON schema object")
    strict: Optional[bool] = Field(
        None,
        description="Whether to enforce strict schema adherence",
    )


class LLMResponseFormat(BaseModel):
    type: LLMResponseFormatEnum = Field(
        ...,
        description="Response format type: 'text', 'json_object', or 'json_schema'",
        example="json_schema",
    )
    json_schema: Optional[LLMResponseSchema] = Field(
        None,
        description="JSON schema definition (required when type is 'json_schema')",
    )

    @model_validator(mode="after")
    def validate_schema_requirement(self):
        if self.type == LLMResponseFormatEnum.JSON_SCHEMA and not self.json_schema:
            raise ValueError(
                "json_schema object is required when using type='json_schema'",
            )
        if (
            self.type != LLMResponseFormatEnum.JSON_SCHEMA
            and self.json_schema is not None
        ):
            raise ValueError(
                f'response format must only be {{"type": "{self.type}"}} when using type="{self.type}"',
            )
        return self

    class Config:
        use_enum_values = True
        extra = "forbid"


class ToolChoiceFunction(BaseModel):
    name: str = Field(..., description="The name of the function")


class ToolChoice(BaseModel):
    type: str = Field(
        default="function",
        description="The type of tool choice. Should always be 'function'",
    )
    function: Optional[ToolChoiceFunction] = Field(
        None,
        description="The tool choice fucntion name",
    )

    @field_validator("type", mode="before")
    @classmethod
    def force_type(cls, v):
        return "function"


class LLMBaseConfigSettings(BaseModel):
    model_config = {"extra": "forbid"}

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


class LLMConfigSettings(LLMBaseConfigSettings):
    model_config = {"extra": "forbid"}

    tool_choice: Optional[Union[ToolChoiceEnum, ToolChoice]] = Field(
        None,
        description="Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)",
    )
    response_format: Optional[Union[LLMResponseFormat, Type[BaseModel]]] = Field(
        None,
        description="Either a structured json_schema or a Pydantic model to enforce structured outputs.",
    )
    stream_options: Optional[StreamOptions] = Field(
        None,
        description="Additional streaming configuration options",
    )
