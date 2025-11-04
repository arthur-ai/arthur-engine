from datetime import datetime
from typing import List, Optional

from litellm.types.llms.anthropic import AnthropicThinkingParam
from pydantic import BaseModel, Field, model_validator

from db_models.llm_eval_models import DatabaseLLMEval
from schemas.agentic_prompt_schemas import LogitBiasItem
from schemas.enums import ModelProvider, ReasoningEffortEnum


class ScoreRange(BaseModel):
    min_score: int = Field(default=0, description="Minimum score for the llm eval")
    max_score: int = Field(default=1, description="Maximum score for the llm eval")

    @model_validator(mode="after")
    def validate_score_range(self):
        if self.min_score >= self.max_score:
            raise ValueError("min_score must be less than max_score")
        return self


class LLMEvalConfig(BaseModel):
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


class LLMEval(BaseModel):
    name: str = Field(description="Name of the llm eval")
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: ModelProvider = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure')",
    )
    instructions: str = Field(description="Instructions for the llm eval")
    score_range: ScoreRange = Field(
        default=ScoreRange(min_score=0, max_score=1),
        description="Score range for the llm eval (defaults to boolean)",
    )
    config: Optional[LLMEvalConfig] = Field(
        default=None,
        description="LLM configurations for this eval (e.g. temperature, max_tokens, etc.)",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the llm eval was created.",
    )
    deleted_at: Optional[datetime] = Field(
        None,
        description="Time that this llm eval was deleted",
    )
    version: int = Field(default=1, description="Version of the llm eval")

    class Config:
        use_enum_values = True

    def has_been_deleted(self) -> bool:
        return self.deleted_at is not None

    @classmethod
    def from_db_model(cls, db_eval: DatabaseLLMEval) -> "LLMEval":
        return cls.model_validate(db_eval.__dict__)

    def to_db_model(self, task_id: str) -> DatabaseLLMEval:
        return DatabaseLLMEval(
            task_id=task_id,
            **self.model_dump(mode="python", exclude_none=True),
        )
