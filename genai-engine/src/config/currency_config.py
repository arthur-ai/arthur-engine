import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class CurrencyConfig(BaseSettings):
    """Configuration for the currency conversion service and rate providers."""

    CURRENCY_PROVIDER_BASE_URL: str = "https://api.frankfurter.dev"
    SUPPORTED_CURRENCIES: Optional[list[str]] = None  # None = use all from provider

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CURRENCY_",
    )


currency_config = CurrencyConfig(
    _env_file=os.environ.get("GENAI_ENGINE_CURRENCY_CONFIG_PATH", ".env"),  # type: ignore[call-arg]
)
