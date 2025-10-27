from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class GenaiEngineOpenAIProvider(Enum):
    OPENAI = "OpenAI"
    AZURE = "Azure"


class OpenAISettings(BaseSettings):
    GENAI_ENGINE_OPENAI_PROVIDER: GenaiEngineOpenAIProvider = (
        GenaiEngineOpenAIProvider.AZURE
    )
    GENAI_ENGINE_OPENAI_RATE_LIMIT_TOKENS_PER_PERIOD: int
    GENAI_ENGINE_OPENAI_RATE_LIMIT_PERIOD_SECONDS: int
    GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS: str | None = Field(...)
    GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS: str | None = Field(
        default=None,
    )
    OPENAI_API_VERSION: str | None = Field(default="2025-02-01-preview")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    @field_validator("GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS")
    def check_url_for_genai_engine_openai_gpt_names_endpoints_keys(
        cls,
        value: str | None,
    ) -> str:
        return _check_url(value, "GENAI_ENGINE_OPENAI_GPT_NAMES_ENDPOINTS_KEYS")

    @classmethod
    @field_validator("GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS")
    def check_url_for_genai_engine_openai_embeddings_names_endpoints_keys(
        cls,
        value: str | None,
    ) -> str:
        if value:
            return _check_url(
                value,
                "GENAI_ENGINE_OPENAI_EMBEDDINGS_NAMES_ENDPOINTS_KEYS",
            )
        return ""


def _check_url(value: str | None, field_name: str) -> str:
    if value is None:
        raise ValueError(
            f"The endpoint URLs in {field_name} must not be None",
        )
    items = value.split(",")
    for item in items:
        endpoint_data = item.split("::")
        url = endpoint_data[1]
        if not url.endswith("/"):
            raise ValueError(
                f"The endpoint URLs in {field_name} must end with '/'",
            )
    return value
