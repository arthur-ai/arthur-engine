import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Type, Union

from litellm import completion, completion_cost
from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.agentic_prompt_models import DatabaseAgenticPrompt


class AgenticPromptRunResponse(BaseModel):
    content: str
    tool_calls: Optional[List[Dict]] = None
    cost: str


class AgenticPromptRunConfig(BaseModel):
    """Request schema for running an agentic prompt"""

    variables: Optional[Dict[str, str]] = Field(
        description="Dictionary of variable names to their values to use for an agentic prompt run",
        default={},
    )
    stream: Optional[bool] = Field(
        description="Whether to stream the response",
        default=False,
    )

    def _replace_match(self, match):
        """Find all {{variable_name}} patterns and replace them"""
        var_name = match.group(1)

        # Return original if not found
        return self.variables.get(var_name, match.group(0))

    def replace_variables(self, messages: List[Dict]) -> List[Dict]:
        """Replace template variables in messages with actual values"""
        updated_messages = []

        for message in messages:
            updated_message = message.copy()
            content = updated_message["content"]

            # Replace all {{variable_name}} patterns
            updated_content = re.sub(
                r"\{\{\s*(\w+)\s*\}\}",
                self._replace_match,
                content,
            )
            updated_message["content"] = updated_content

            updated_messages.append(updated_message)

        return updated_messages


class AgenticPromptBaseConfig(BaseModel):
    messages: List[Dict] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: str = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure')",
    )
    tools: Optional[List[Dict]] = Field(
        None,
        description="Available tools/functions for the model to call, in OpenAI function calling format",
    )
    tool_choice: Optional[Union[str, dict]] = Field(
        None,
        description="Tool choice configuration ('auto', 'none', or specific tool selection)",
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
    logit_bias: Optional[dict] = Field(
        None,
        description="Modify likelihood of specified tokens appearing in completion",
    )
    max_completion_tokens: Optional[int] = Field(
        None,
        description="Maximum number of completion tokens (alternative to max_tokens)",
    )
    reasoning_effort: Optional[
        Literal["none", "minimal", "low", "medium", "high", "default"]
    ] = Field(
        None,
        description="Reasoning effort level for models that support it (e.g., OpenAI o1 series)",
    )
    thinking: Optional[AnthropicThinkingParam] = Field(
        None,
        description="Anthropic-specific thinking parameter for Claude models",
    )
    stream_options: Optional[dict] = Field(
        None,
        description="Additional streaming configuration options",
    )


class AgenticPrompt(AgenticPromptBaseConfig):
    name: str = Field(description="Name of the agentic prompt")

    def run_chat_completion(
        self,
        run_config: AgenticPromptRunConfig = AgenticPromptRunConfig(),
    ) -> Dict[str, Any]:
        model = self.model_provider + "/" + self.model_name

        completion_params = self.model_dump(
            exclude={"name", "model_name", "model_provider"},
        )

        if run_config.variables:
            completion_params["messages"] = run_config.replace_variables(
                completion_params["messages"],
            )

        completion_params["stream"] = run_config.stream

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


class AgenticPromptUnsavedRunConfig(AgenticPrompt, AgenticPromptRunConfig):
    """Request schema for running an unsaved agentic prompt"""

    def _to_prompt_and_config(self) -> Tuple[AgenticPrompt, AgenticPromptRunConfig]:
        """Split into separate prompt and run config objects"""
        prompt_data = self.model_dump(exclude={"variables", "stream"})
        prompt = AgenticPrompt(**prompt_data)
        config = AgenticPromptRunConfig(variables=self.variables, stream=self.stream)
        return prompt, config

    def run_unsaved_prompt(self) -> AgenticPromptRunResponse:
        """Run the unsaved prompt"""
        prompt, config = self._to_prompt_and_config()
        return prompt.run_chat_completion(config)


class AgenticPrompts(BaseModel):
    prompts: List[AgenticPrompt]


class AgenticPromptRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_prompt(self, **kwargs) -> AgenticPrompt:
        return AgenticPrompt(**kwargs)

    def run_unsaved_prompt(
        self,
        run_config: AgenticPromptUnsavedRunConfig,
    ) -> AgenticPromptRunResponse:
        return run_config.run_unsaved_prompt()

    def run_saved_prompt(
        self,
        task_id: str,
        prompt_name: str,
        run_config: AgenticPromptRunConfig = AgenticPromptRunConfig(),
    ) -> AgenticPromptRunResponse:
        prompt = self.get_prompt(task_id, prompt_name)
        return prompt.run_chat_completion(run_config)

    def get_prompt(self, task_id: str, prompt_name: str) -> AgenticPrompt:
        """Get a prompt by task_id and name, return as AgenticPrompt object"""
        db_prompt = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt_name,
            )
            .first()
        )

        if not db_prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        # Convert database model back to AgenticPrompt object
        return AgenticPrompt.from_db_model(db_prompt)

    def get_all_prompts(self, task_id: str) -> AgenticPrompts:
        """Get all prompts by task_id, return as list of AgenticPrompt objects"""
        db_prompts = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(DatabaseAgenticPrompt.task_id == task_id)
            .all()
        )

        prompts = [AgenticPrompt.from_db_model(db_prompt) for db_prompt in db_prompts]
        return AgenticPrompts(prompts=prompts)

    def save_prompt(self, task_id: str, prompt: AgenticPrompt | Dict[str, Any]) -> None:
        """Save an AgenticPrompt to the database"""
        if isinstance(prompt, dict):
            prompt = self.create_prompt(**prompt)

        db_prompt = prompt.to_db_model(task_id)

        try:
            self.db_session.add(db_prompt)
            self.db_session.commit()
        except IntegrityError:
            self.db_session.rollback()
            raise ValueError(
                f"Prompt '{prompt.name}' already exists for task '{task_id}'",
            )

    def delete_prompt(self, task_id: str, prompt_name: str) -> None:
        """Delete an agentic prompt from the database"""
        db_prompt = (
            self.db_session.query(DatabaseAgenticPrompt)
            .filter(
                DatabaseAgenticPrompt.task_id == task_id,
                DatabaseAgenticPrompt.name == prompt_name,
            )
            .first()
        )

        if not db_prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found for task '{task_id}'")

        self.db_session.delete(db_prompt)
        self.db_session.commit()
