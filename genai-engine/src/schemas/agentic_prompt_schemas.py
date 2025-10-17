import warnings
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from jinja2.sandbox import SandboxedEnvironment
from litellm import acompletion, completion, completion_cost, stream_chunk_builder
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from schemas.common_schemas import JsonSchema
from schemas.enums import (
    LLMResponseFormatEnum,
    MessageRole,
    ProviderEnum,
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

    def replace_variables(self, messages: List[Dict]) -> List[Dict]:
        updated_messages = []

        for message in messages:
            updated_message = message.copy()
            template = self._jinja_env.from_string(updated_message["content"])
            updated_message["content"] = template.render(**self._variable_map)
            updated_messages.append(updated_message)

        return updated_messages


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


class AgenticPromptMessage(BaseModel):
    role: MessageRole = Field(description="Role of the message")
    content: Optional[str] = Field(default=None, description="Content of the message")
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


class AgenticPromptBaseConfig(BaseModel):
    messages: List[AgenticPromptMessage] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: ProviderEnum = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure')",
    )
    tools: Optional[List[LLMTool]] = Field(
        None,
        description="Available tools/functions for the model to call, in OpenAI function calling format",
    )
    tool_choice: Optional[Union[ToolChoiceEnum, ToolChoice]] = Field(
        None,
        description="Tool choice configuration ('auto', 'none', 'required', or a specific tool selection)",
    )
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
    response_format: Optional[LLMResponseFormat] = Field(
        None,
        description="Response format specification (e.g., {'type': 'json_object'} for JSON mode)",
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
    stream_options: Optional[StreamOptions] = Field(
        None,
        description="Additional streaming configuration options",
    )

    class Config:
        use_enum_values = True


class AgenticPrompt(AgenticPromptBaseConfig):
    name: str = Field(description="Name of the agentic prompt")

    def _get_completion_params(
        self,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> Tuple[str, Dict[str, Any]]:
        model = self.model_provider + "/" + self.model_name

        completion_params = self.model_dump(
            exclude={"name", "model_name", "model_provider"},
            exclude_none=True,
        )

        if completion_request.variables:
            completion_params["messages"] = completion_request.replace_variables(
                completion_params["messages"],
            )

        if completion_request.stream is not None:
            completion_params["stream"] = completion_request.stream

        # not allowed to have tool_choice if no tools are provided
        if self.tools is None:
            completion_params.pop("tool_choice", None)

        return model, completion_params

    def run_chat_completion(
        self,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> AgenticPromptRunResponse:
        model, completion_params = self._get_completion_params(completion_request)
        response = completion(model=model, **completion_params)

        cost = completion_cost(response)
        msg = response.choices[0].message

        return AgenticPromptRunResponse(
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            cost=f"{cost:.6f}",
        )

    async def stream_chat_completion(
        self,
        completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    ) -> AsyncGenerator[str, None]:
        model, completion_params = self._get_completion_params(completion_request)
        response = await acompletion(model=model, **completion_params)

        collected_chunks = []
        async for chunk in response:
            collected_chunks.append(chunk)
            yield f"event: chunk\ndata: {chunk.model_dump_json()}\n\n"

        # Build complete response from chunks
        complete_response = stream_chunk_builder(
            collected_chunks,
            messages=completion_params.get("messages", []),
        )

        cost = completion_cost(complete_response)
        msg = complete_response.choices[0].message

        # yield the final response
        yield f"event: final_response\ndata: {
            AgenticPromptRunResponse(
                content=msg.get("content"),
                tool_calls=msg.get("tool_calls"),
                cost=f"{cost:.6f}",
            ).model_dump_json()
        }\n\n"

    @classmethod
    def from_db_model(cls, db_prompt: DatabaseAgenticPrompt) -> "AgenticPrompt":
        # Base fields that map directly
        base_fields = {
            "name": db_prompt.name,
            "messages": db_prompt.messages,
            "model_name": db_prompt.model_name,
            "model_provider": db_prompt.model_provider,
            "tools": db_prompt.tools,
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
        base_fields = {k: v for k, v in prompt_dict.items() if k not in config_keys}

        return DatabaseAgenticPrompt(
            task_id=task_id,
            created_at=datetime.now(),
            **base_fields,
            config=config or None,
        )


class CompletionRequest(AgenticPromptBaseConfig):
    """Request schema for running an unsaved agentic prompt"""

    completion_request: PromptCompletionRequest = Field(
        default=PromptCompletionRequest(),
        description="Run configuration for the unsaved prompt",
    )

    def to_prompt_and_request(self) -> Tuple[AgenticPrompt, PromptCompletionRequest]:
        prompt = AgenticPrompt(
            name="test_unsaved_prompt",
            **self.model_dump(exclude={"completion_request"}),
        )
        return prompt, self.completion_request


class AgenticPrompts(BaseModel):
    prompts: List[AgenticPrompt]
