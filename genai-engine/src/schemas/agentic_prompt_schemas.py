import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from litellm import completion, completion_cost
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_serializer,
    field_validator,
    model_validator,
)

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from schemas.response_schemas import AgenticPromptRunResponse


class ProviderEnum(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"
    AZURE = "azure"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    META_LLAMA = "meta_llama"
    GROQ = "groq"
    BEDROCK = "bedrock"
    SAGEMAKER = "sagemaker"
    VERTEX_AI = "vertex_ai"
    HUGGINGFACE = "huggingface"
    CLOUDFLARE = "cloudflare"
    AI21 = "ai21"
    BASETEN = "baseten"
    COHERE = "cohere"
    EMPOWER = "empower"
    FEATHERLESS_AI = "featherless_ai"
    FRIENDLIAI = "friendliai"
    GALADRIEL = "galadriel"
    NEBIUS = "nebius"
    NLP_CLOUD = "nlp_cloud"
    NOVITA = "novita"
    OPENROUTER = "openrouter"
    PETALS = "petals"
    REPLICATE = "replicate"
    TOGETHER_AI = "together_ai"
    VLLM = "vllm"
    WATSONX = "watsonx"


class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    AI = "ai"
    TOOL = "tool"


class ReasoningEffortEnum(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DEFAULT = "default"


class ToolChoiceEnum(str, Enum):
    AUTO = "auto"
    NONE = "none"
    REQUIRED = "required"


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

    @model_validator(mode="after")
    def _build_variable_map(self):
        """Construct a private lookup dictionary for variable substitution"""
        if self.variables:
            self._variable_map = {v.name: v.value for v in self.variables}
        return self

    def _replace_match(self, match):
        """Find all {{variable_name}} patterns and replace them"""
        var_name = match.group(1)

        # Return original if not found
        return self._variable_map.get(var_name, match.group(0))

    def replace_variables(self, messages: List[Dict]) -> List[Dict]:
        """Replace template variables in messages with actual values"""
        updated_messages = []

        for message in messages:
            updated_message = message.copy()
            content = updated_message["content"]

            # Replace all {{variable_name}} patterns
            updated_content = re.sub(
                r"\{\{\s*([^\{\}]+?)\s*\}\}",
                self._replace_match,
                content,
            )
            updated_message["content"] = updated_content

            updated_messages.append(updated_message)

        return updated_messages


class AgenticPromptMessage(BaseModel):
    role: MessageRole = Field(Description="Role of the message")
    content: str = Field(Description="Content of the message")

    @field_serializer("role")
    def serialize_role(self, v, _info):
        return v.value

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


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
    tools: Optional[List[Dict]] = Field(
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
    response_format: Optional[Union[dict, Type[BaseModel]]] = Field(
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

    def model_dump(self, **kwargs):
        """Override to auto-format tool_choice before dumping."""
        data = super().model_dump(**kwargs)
        tool_choice = data.get("tool_choice")

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
        model = self.model_provider + "/" + self.model_name

        completion_params = self.model_dump(
            exclude={"name", "model_name", "model_provider"},
        )

        if run_config.variables:
            completion_params["messages"] = run_config.replace_variables(
                completion_params["messages"],
            )

        completion_params["stream"] = run_config.stream

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
