from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

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
    variables: List[str] = Field(
        default_factory=list,
        description="List of variable names for the llm eval",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags for this llm eval version",
    )
    config: Optional[LLMBaseConfigSettings] = Field(
        default=None,
        description="LLM configurations for this eval (e.g. temperature, max_tokens, etc.)",
    )
    created_at: datetime = Field(
        ...,
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


class ReasonedScore(BaseModel):
    """
    Response format schema for llm eval runs
    """

    reason: str = Field(
        ...,
        description="Explanation for how you arrived at this answer.",
    )
    score: int = Field(..., ge=0, le=1, description="Binary score between 0 and 1")
