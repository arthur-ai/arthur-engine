from datetime import datetime
from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,
)

from schemas.enums import (
    ModelProvider,
)
from schemas.llm_schemas import LLMConfigSettings, LLMTool, OpenAIMessage


class AgenticPrompt(BaseModel):
    name: str = Field(description="Name of the agentic prompt")
    messages: List[OpenAIMessage] = Field(
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
    variables: List[str] = Field(
        default_factory=list,
        description="List of variable names for the agentic prompt",
    )
    config: Optional[LLMConfigSettings] = Field(
        default=None,
        description="LLM configurations for this prompt (e.g. temperature, max_tokens, etc.)",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the prompt was created.",
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Time that this prompt was deleted",
    )

    class Config:
        use_enum_values = True

    def has_been_deleted(self) -> bool:
        return self.deleted_at is not None
