from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from schemas.enums import ModelProvider
from schemas.llm_schemas import (
    LLMBaseConfigSettings,
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
    min_score: int = Field(default=0, description="Minimum score for the llm eval")
    max_score: int = Field(default=1, description="Maximum score for the llm eval")
    variables: List[str] = Field(
        default_factory=list,
        description="List of variable names for the llm eval",
    )
    config: Optional[LLMBaseConfigSettings] = Field(
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

    @model_validator(mode="after")
    def validate_score_range(self):
        if self.min_score >= self.max_score:
            raise ValueError("min_score must be less than max_score")
        return self

    def has_been_deleted(self) -> bool:
        return self.deleted_at is not None
