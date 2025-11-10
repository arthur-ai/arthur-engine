import warnings
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple, Union

from jinja2 import meta
from jinja2.sandbox import SandboxedEnvironment
from litellm import (
    completion_cost,
    stream_chunk_builder,
)
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from clients.llm.llm_client import LLMClient
from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from schemas.common_schemas import JsonSchema
from schemas.enums import (
    LLMResponseFormatEnum,
    MessageRole,
    ModelProvider,
    OpenAIMessageType,
    ReasoningEffortEnum,
    ToolChoiceEnum,
)
from schemas.response_schemas import AgenticPromptRunResponse

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


class VariableTemplateValue(BaseModel):
    name: str = Field(..., description="Name of the variable")
    value: str = Field(..., description="Value of the variable")


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


class AgenticPromptMessage(BaseModel):
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


class PromptCompletionRequest(BaseModel):
    """Request schema for running an agentic prompt"""

    variables: Optional[List[VariableTemplateValue]] = Field(
        description="List of VariableTemplateValue fields that specify the values to fill in for each template in the prompt",
        default=[],
    )
    stream: Optional[bool] = Field(
        description="Whether to stream the response",
        default=False,
    )
    strict: Optional[bool] = Field(
        description="Whether to enforce strict validation of variables. If True, any variables that are found in the prompt but not in the variables list will raise an error.",
        default=False,
    )

    _variable_map: Dict[str, str] = PrivateAttr(default_factory=dict)

    # autoescape=False because Jinja automatically HTML-escapes items by default. Ex:
    #   if text = "{{ name }}" and variables = {"name": "<Bob>"}
    #   autoescape=False "{{ name }}" -> "<Bob>"
    #   autoescape=True "{{ name }}" -> "&lt;Bob&gt;"
    _jinja_env: SandboxedEnvironment = PrivateAttr(
        default_factory=lambda: SandboxedEnvironment(autoescape=False),
    )

    @model_validator(mode="after")
    def _build_variable_map(self):
        """Construct a private lookup dictionary for variable substitution"""
        if self.variables:
            self._variable_map = {v.name: v.value for v in self.variables}
        return self

    def _find_missing_variables_in_text(self, text: str) -> List[str]:
        template_ast = self._jinja_env.parse(text)
        undeclared_vars = meta.find_undeclared_variables(template_ast)
        return [v for v in undeclared_vars if v not in self._variable_map]

    def find_missing_variables(self, messages: List[AgenticPromptMessage]) -> Set[str]:
        missing_vars = set()
        for message in messages:
            if message.content is None:
                continue

            if isinstance(message.content, str):
                missing_vars.update(
                    self._find_missing_variables_in_text(message.content),
                )
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.type == OpenAIMessageType.TEXT.value and item.text:
                        missing_vars.update(
                            self._find_missing_variables_in_text(item.text),
                        )

        return missing_vars

    def _replace_variables_in_text(self, text: str) -> str:
        template = self._jinja_env.from_string(text)
        return template.render(**self._variable_map)

    def replace_variables(self, messages: List[AgenticPromptMessage]) -> list[dict]:
        for message in messages:
            if message.content is None:
                continue

            if isinstance(message.content, str):
                message.content = self._replace_variables_in_text(message.content)
            elif isinstance(message.content, list):
                for item in message.content:
                    if item.type == OpenAIMessageType.TEXT.value and item.text:
                        item.text = self._replace_variables_in_text(item.text)

        return messages


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

    class Config:
        use_enum_values = True


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


class LLMConfigSettings(BaseModel):
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


class AgenticPromptBaseConfig(LLMConfigSettings):
    messages: List[AgenticPromptMessage] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: ModelProvider = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure')",
    )
    version: int = Field(default=1, description="Version of the agentic prompt")
    tools: Optional[List[LLMTool]] = Field(
        None,
        description="Available tools/functions for the model to call, in OpenAI function calling format",
    )
    tool_choice: Optional[Union[ToolChoiceEnum, ToolChoice]] = Field(
        None,
        description="Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)",
    )
    response_format: Optional[LLMResponseFormat] = Field(
        None,
        description="Response format specification (e.g., {'type': 'json_object'} for JSON mode)",
    )
    stream_options: Optional[StreamOptions] = Field(
        None,
        description="Additional streaming configuration options",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the prompt was created.",
    )
    deleted_at: Optional[datetime] = Field(
        None,
        description="Time that this prompt was deleted",
    )

    class Config:
        use_enum_values = True

    def has_been_deleted(self) -> bool:
        return self.deleted_at is not None


class AgenticPrompt(AgenticPromptBaseConfig):
    name: str = Field(description="Name of the agentic prompt")

    def _get_completion_params(
        self,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> Tuple[str, Dict[str, Any]]:
        model = self.model_provider + "/" + self.model_name

        completion_params = self.model_dump(
            exclude={
                "name",
                "model_name",
                "model_provider",
                "created_at",
                "version",
                "deleted_at",
                "messages",
            },
            exclude_none=True,
        )

        # validate all variables are passed in to the prompt if strict mode is enabled
        if completion_request.strict == True:
            missing_vars = completion_request.find_missing_variables(
                self.messages,
            )
            if missing_vars:
                raise ValueError(
                    f"Missing values for the following variables: {', '.join(sorted(missing_vars))}",
                )

        # replace variables in messages
        completion_messages = self.messages
        if completion_request.variables:
            completion_messages = completion_request.replace_variables(
                completion_messages,
            )

        completion_params["messages"] = [
            message.model_dump(exclude_none=True) for message in completion_messages
        ]

        if completion_request.stream is not None:
            completion_params["stream"] = completion_request.stream

        # not allowed to have tool_choice if no tools are provided
        if self.tools is None:
            completion_params.pop("tool_choice", None)

        return model, completion_params

    def run_chat_completion(
        self,
        llm_client: LLMClient,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> AgenticPromptRunResponse:
        if self.has_been_deleted():
            raise ValueError(
                f"Cannot run chat completion for this prompt because it was deleted on: {self.deleted_at}",
            )

        model, completion_params = self._get_completion_params(completion_request)
        response = llm_client.completion(model=model, **completion_params)

        cost = completion_cost(response)
        msg = response.choices[0].message

        return AgenticPromptRunResponse(
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            cost=f"{cost:.6f}",
        )

    async def stream_chat_completion(
        self,
        llm_client: LLMClient,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> AsyncGenerator[str, None]:
        try:
            if self.has_been_deleted():
                raise ValueError(
                    f"Cannot stream chat completion for this prompt because it was deleted on: {self.deleted_at}",
                )

            model, completion_params = self._get_completion_params(completion_request)
            response = await llm_client.acompletion(model=model, **completion_params)

            collected_chunks = []
            async for chunk in response:
                collected_chunks.append(chunk)
                yield f"event: chunk\ndata: {chunk.model_dump_json()}\n\n"

            complete_response = stream_chunk_builder(
                collected_chunks,
                messages=completion_params.get("messages", []),
            )

            cost = completion_cost(complete_response)
            msg = complete_response.choices[0].message

            yield f"event: final_response\ndata: {
                AgenticPromptRunResponse(
                    content=msg.get("content"),
                    tool_calls=msg.get("tool_calls"),
                    cost=f"{cost:.6f}",
                ).model_dump_json()
            }\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    @classmethod
    def from_db_model(cls, db_prompt: DatabaseAgenticPrompt) -> "AgenticPrompt":
        # Base fields that map directly
        base_fields = {
            "name": db_prompt.name,
            "messages": db_prompt.messages,
            "model_name": db_prompt.model_name,
            "model_provider": db_prompt.model_provider,
            "tools": db_prompt.tools,
            "created_at": db_prompt.created_at,
            "version": db_prompt.version,
            "deleted_at": db_prompt.deleted_at,
        }

        # Merge in config JSON if present (LLM parameters)
        if db_prompt.config:
            base_fields.update(db_prompt.config)

        return cls(**base_fields)

    def to_db_model(self, task_id: str) -> DatabaseAgenticPrompt:
        """Convert this AgenticPrompt into a DatabaseAgenticPrompt"""
        # Flatten model and extract config fields
        prompt_dict = self.model_dump()

        config_keys = {
            "tool_choice",
            "timeout",
            "temperature",
            "top_p",
            "stream",
            "max_tokens",
            "response_format",
            "stop",
            "presence_penalty",
            "frequency_penalty",
            "seed",
            "logprobs",
            "top_logprobs",
            "logit_bias",
            "max_completion_tokens",
            "reasoning_effort",
            "thinking",
            "stream_options",
        }

        config = {
            k: v for k, v in prompt_dict.items() if k in config_keys and v is not None
        }
        base_fields = {
            k: v
            for k, v in prompt_dict.items()
            if k not in config_keys and k != "created_at"
        }

        return DatabaseAgenticPrompt(
            task_id=task_id,
            **base_fields,
            config=config or None,
        )


class CompletionRequest(AgenticPromptBaseConfig):
    """Request schema for running an unsaved agentic prompt"""

    completion_request: PromptCompletionRequest = Field(
        default_factory=PromptCompletionRequest,
        description="Run configuration for the unsaved prompt",
    )

    def to_prompt_and_request(self) -> Tuple[AgenticPrompt, PromptCompletionRequest]:
        prompt = AgenticPrompt(
            name="test_unsaved_prompt",
            **self.model_dump(exclude={"completion_request"}),
        )
        return prompt, self.completion_request
