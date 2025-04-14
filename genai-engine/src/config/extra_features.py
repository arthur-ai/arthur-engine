from pydantic_settings import BaseSettings, SettingsConfigDict


class ExtraFeaturesSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="GENAI_ENGINE_",
    )


extra_feature_config = ExtraFeaturesSettings()
