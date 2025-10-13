from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from jinja2.sandbox import SandboxedEnvironment
from litellm import completion, completion_cost
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
)

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from schemas.common_schemas import JsonSchema
from schemas.enums import MessageRole, ProviderEnum, ReasoningEffortEnum, ToolChoiceEnum
from schemas.response_schemas import AgenticPromptRunResponse


class StreamOptions(BaseModel):
    include_usage: Optional[bool] = Field(
        None,
        description="Whether to include usage information in the stream",
    )


class VariableTemplateValue(BaseModel):
    name: str = Field(..., Description="Name of the variable")
    value: str = Field(..., Description="Value of the variable")


class LogitBiasItem(BaseModel):
    token_id: int = Field(..., description="Token ID to bias")
    bias: float = Field(..., description="Bias value between -100 and 100")

    @field_validator("bias")
    @classmethod
    def validate_bias(cls, v):
        if not -100 <= v <= 100:
            raise ValueError("Bias must be between -100 and 100.")
        return v


class AgenticPromptRunConfig(BaseModel):
    """Request schema for running an agentic prompt"""

    variables: Optional[List[VariableTemplateValue]] = Field(
        description="Dictionary of variable names to their values to use for an agentic prompt run",
        default=[],
    )
    stream: Optional[bool] = Field(
        description="Whether to stream the response",
        default=False,
    )

    _variable_map: Dict[str, str] = PrivateAttr(default_factory=dict)
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

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments}


class ToolCall(BaseModel):
    id: str = Field(..., description="Unique identifier for the tool call")
    type: str = Field(default="function", description="Type of tool call")
    function: ToolCallFunction = Field(..., description="Function details")

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type, "function": self.function.to_dict()}


class AgenticPromptMessage(BaseModel):
    role: MessageRole = Field(Description="Role of the message")
    content: Optional[str] = Field(default=None, Description="Content of the message")
    tool_calls: Optional[List[ToolCall]] = Field(
        default=None,
        Description="Tool calls made by assistant",
    )
    tool_call_id: Optional[str] = Field(
        default=None,
        Description="ID of the tool call this message is responding to",
    )

    @field_serializer("role")
    def serialize_role(self, v, _info):
        return v.value

    def to_dict(self) -> Dict[str, Any]:
        result = {"role": self.role.value}

        if self.content is not None:
            result["content"] = self.content

        if self.tool_calls is not None:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]

        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id

        return result


class LLMTool(BaseModel):
    name: str = Field(..., description="The name of the tool/function")
    description: Optional[str] = Field(
        default=None,
        description="Description of what the tool does",
    )
    function_definition: Optional[JsonSchema] = Field(
        default=None,
        description="The function's parameter schema",
    )
    strict: Optional[bool] = Field(
        default=None,
        description="Whether the function definition should use OpenAI's strict mode",
    )

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": "function", "function": {"name": self.name}}

        if self.description:
            result["function"]["description"] = self.description

        if self.strict is not None:
            result["strict"] = self.strict

        if self.function_definition:
            result["function"]["parameters"] = self.function_definition.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMTool":
        function_definition = None
        if "parameters" in data["function"]:
            function_definition = JsonSchema.from_dict(data["function"]["parameters"])

        return cls(
            name=data["function"]["name"],
            description=data["function"].get("description"),
            function_definition=function_definition,
            strict=data.get("strict"),
        )


class LLMResponseSchema(BaseModel):
    name: str = Field(..., description="Name of the schema")
    description: Optional[str] = Field(None, description="Description of the schema")
    json_schema: JsonSchema = Field(..., description="The JSON schema object")
    strict: Optional[bool] = Field(
        None,
        description="Whether to enforce strict schema adherence",
    )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "schema": self.json_schema.to_dict(),
        }

        if self.description:
            result["description"] = self.description

        if self.strict is not None:
            result["strict"] = self.strict

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponseSchema":
        return cls(
            name=data["name"],
            description=data.get("description"),
            json_schema=JsonSchema.from_dict(data["schema"]),
            strict=data.get("strict"),
        )


class LLMResponseFormat(BaseModel):
    type: str = Field(
        ...,
        description="Response format type: 'text', 'json_object', or 'json_schema'",
    )
    response_schema: Optional[LLMResponseSchema] = Field(
        None,
        description="JSON schema definition (required when type is 'json_schema')",
    )

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}

        if self.response_schema:
            result["json_schema"] = self.response_schema.to_dict()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMResponseFormat":
        if data.get("type") == "json_schema" and "json_schema" in data:
            return cls(
                type=data["type"],
                response_schema=LLMResponseSchema.from_dict(data["json_schema"]),
            )
        else:
            return cls(type=data["type"])


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
    tool_choice: Optional[Union[ToolChoiceEnum, str]] = Field(
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

    @field_validator("tools", mode="before")
    @classmethod
    def convert_tools(cls, v):
        if v is None:
            return v

        return [
            LLMTool.from_dict(tool) if isinstance(tool, dict) else tool for tool in v
        ]

    @field_validator("response_format", mode="before")
    @classmethod
    def convert_response_format(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return LLMResponseFormat.from_dict(v)
        return v

    def model_dump(self, **kwargs):
        """Override to auto-format tool_choice before dumping."""
        data = super().model_dump(**kwargs)
        tool_choice = data.get("tool_choice")

        if data.get("messages"):
            data["messages"] = [message.to_dict() for message in self.messages]

        if data.get("tools"):
            data["tools"] = [tool.to_dict() for tool in self.tools]

        if data.get("response_format") and self.response_format:
            data["response_format"] = self.response_format.to_dict()

        if isinstance(tool_choice, ToolChoiceEnum):
            data["tool_choice"] = tool_choice.value
        elif isinstance(tool_choice, str) and tool_choice not in {
            "auto",
            "none",
            "required",
        }:
            data["tool_choice"] = {
                "type": "function",
                "function": {"name": tool_choice},
            }

        return data


class AgenticPrompt(AgenticPromptBaseConfig):
    name: str = Field(description="Name of the agentic prompt")

    def run_chat_completion(
        self,
        run_config: AgenticPromptRunConfig = AgenticPromptRunConfig(),
    ) -> AgenticPromptRunResponse:
        model = self.model_provider.value + "/" + self.model_name

        completion_params = self.model_dump(
            exclude={"name", "model_name", "model_provider"},
        )

        if run_config.variables:
            completion_params["messages"] = run_config.replace_variables(
                completion_params["messages"],
            )

        # TODO: Re-implement streaming to actually work
        # completion_params["stream"] = run_config.stream

        # not allowed to have tool_choice if no tools are provided
        if self.tools is None:
            completion_params.pop("tool_choice", None)

        response = completion(model=model, **completion_params)

        cost = completion_cost(response)
        msg = response.choices[0].message

        return AgenticPromptRunResponse(
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            cost=f"{cost:.6f}",
        )

    @model_serializer(mode="wrap")
    def serialize_model(self, serializer):
        data = serializer(self)

        if data.get("tools"):
            data["tools"] = [tool.to_dict() for tool in self.tools]

        if data.get("response_format") and self.response_format:
            data["response_format"] = self.response_format.to_dict()

        tool_choice = data.get("tool_choice")
        if tool_choice is not None and tool_choice not in ["auto", "none", "required"]:
            data["tool_choice"] = {
                "type": "function",
                "function": {"name": tool_choice},
            }

        return data

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

        if db_prompt.tools:
            base_fields["tools"] = [LLMTool.from_dict(tool) for tool in db_prompt.tools]

        # Merge in config JSON if present (LLM parameters)
        if db_prompt.config:
            config = db_prompt.config.copy()

            if "tool_choice" in config:
                if isinstance(config["tool_choice"], dict):
                    config["tool_choice"] = config["tool_choice"]["function"]["name"]
                elif isinstance(config["tool_choice"], str) and config[
                    "tool_choice"
                ] in ["auto", "none", "required"]:
                    config["tool_choice"] = ToolChoiceEnum(config["tool_choice"])

            if "response_format" in config and isinstance(
                config["response_format"],
                dict,
            ):
                config["response_format"] = LLMResponseFormat.from_dict(
                    config["response_format"],
                )

            base_fields.update(config)

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

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AgenticPromptUnsavedRunConfig(AgenticPromptBaseConfig):
    """Request schema for running an unsaved agentic prompt"""

    run_config: AgenticPromptRunConfig = Field(
        default=AgenticPromptRunConfig(),
        description="Run configuration for the unsaved prompt",
    )

    def run_unsaved_prompt(self) -> AgenticPromptRunResponse:
        """Run the unsaved prompt"""
        prompt = AgenticPrompt(
            name="test_unsaved_prompt",
            **self.model_dump(exclude={"run_config"}),
        )
        return prompt.run_chat_completion(self.run_config)


class AgenticPrompts(BaseModel):
    prompts: List[AgenticPrompt]
