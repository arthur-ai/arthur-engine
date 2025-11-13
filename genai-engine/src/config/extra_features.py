from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtraFeaturesSettings(BaseSettings):
    CHAT_ENABLED: bool = Field(default=False, alias="CHAT_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="GENAI_ENGINE_",
    )

    @field_validator("CHAT_ENABLED", mode="before")
    def validate_chat_enabled(cls, v: Any) -> bool:
        if not v:
            return False
        if isinstance(v, str):
            return v.lower() == "enabled"
        elif isinstance(v, bool):
            return v
        else:
            raise ValueError(
                "CHAT_ENABLED must be a boolean or a string with value 'enabled'/'disabled'",
            )


extra_feature_config = ExtraFeaturesSettings()
