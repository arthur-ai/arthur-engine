from typing import Literal

from arthur_common.models.llm_model_providers import ModelProvider
from pydantic import BaseModel, ConfigDict, field_validator


class GuardrailLLMConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: ModelProvider
    model: str
    base_model: str | None = None

    @field_validator("model", "base_model")
    @classmethod
    def nonempty_model(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Model must not be empty.")
        return value


GuardrailLLMStatus = Literal["configured", "needs_configuration", "invalid"]
