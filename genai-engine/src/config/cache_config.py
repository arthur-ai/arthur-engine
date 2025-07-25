import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheConfig(BaseSettings):
    TASK_RULES_CACHE_ENABLED: bool = "PYTEST_CURRENT_TEST" not in os.environ
    TASK_RULES_CACHE_TTL: int = 60 * 1
    
    TASK_METRICS_CACHE_ENABLED: bool = "PYTEST_CURRENT_TEST" not in os.environ
    TASK_METRICS_CACHE_TTL: int = 60 * 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CACHE_",
    )


cache_config = CacheConfig(
    _env_file=os.environ.get("GENAI_ENGINE_CACHE_CONFIG_PATH", ".env"),
)
