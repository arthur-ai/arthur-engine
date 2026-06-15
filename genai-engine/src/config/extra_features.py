from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtraFeaturesSettings(BaseSettings):
    CHATBOT_ENABLED: bool = Field(default=True, alias="CHATBOT_ENABLED")
    # Aliased to the canonical env var so registration-time and the
    # handler's `Config.demo_mode()` check read the same source. The
    # other flags in this class use unprefixed aliases ("CHATBOT_ENABLED"
    # etc.); demo mode predates this class and has always been
    # `GENAI_ENGINE_DEMO_MODE`.
    DEMO_MODE: bool = Field(default=False, alias="GENAI_ENGINE_DEMO_MODE")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="GENAI_ENGINE_",
    )

    @field_validator(
        "CHATBOT_ENABLED",
        "DEMO_MODE",
        mode="before",
    )
    def validate_feature_flag(cls, v: Any) -> bool:
        if not v:
            return False
        if isinstance(v, str):
            return v.lower() == "enabled"
        elif isinstance(v, bool):
            return v
        else:
            raise ValueError(
                "Value must be a boolean or a string with value 'enabled'/'disabled'",
            )


extra_feature_config = ExtraFeaturesSettings()
