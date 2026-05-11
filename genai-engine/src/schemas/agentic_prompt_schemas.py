from datetime import datetime
from typing import List, Literal, Optional, Union

from arthur_common.models.llm_model_providers import (
    LLMConfigSettings,
    LLMTool,
    ModelProvider,
    OpenAIMessage,
)
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from utils.constants import EMPTY_MODEL_PROVIDER


class AgenticPrompt(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(description="Name of the agentic prompt")
    messages: List[OpenAIMessage] = Field(
        description="List of chat messages in OpenAI format (e.g., [{'role': 'user', 'content': 'Hello'}])",
    )
    model_name: str = Field(
        description="Name of the LLM model (e.g., 'gpt-4o', 'claude-3-sonnet')",
    )
    model_provider: Union[ModelProvider, Literal["empty"]] = Field(
        description="Provider of the LLM model (e.g., 'openai', 'anthropic', 'azure'). "
        f"The sentinel value '{EMPTY_MODEL_PROVIDER}' indicates the system default placeholder has not been configured.",
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
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags for this agentic prompt version",
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

    def has_been_deleted(self) -> bool:
        return self.deleted_at is not None

    def require_configured_provider(self) -> ModelProvider:
        """Narrow ``model_provider`` to a concrete ``ModelProvider`` or raise.

        ``model_provider`` is ``Union[ModelProvider, Literal["empty"]]`` to
        support the SDG placeholder sentinel, but most downstream code paths
        (LLM client, request/response schemas) require a real provider. Call
        this at the boundary to fail early with a clear error.
        """
        if self.model_provider == EMPTY_MODEL_PROVIDER:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Prompt '{self.name}' has no model provider configured. "
                    "Update the prompt to set a valid model provider before "
                    "using it."
                ),
            )
        return ModelProvider(self.model_provider)
