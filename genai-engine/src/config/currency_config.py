import os
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class CurrencyConfig(BaseSettings):
    """Configuration for the currency conversion service and rate providers."""

    CURRENCY_PROVIDER_BASE_URL: str = "https://api.frankfurter.dev"
    SUPPORTED_CURRENCIES: Optional[list[str]] = None  # None = use all from provider
    DEFAULT_CURRENCY: str = "USD"
    CURRENCY_PROVIDER: Literal["frankfurter", "static"] = "frankfurter"
    CURRENCY_EXCHANGE_RATE: Optional[float] = None  # Required when CURRENCY_PROVIDER=static
    CURRENCY_PROVIDER_API_KEY: Optional[str] = None  # Optional; Frankfurter does not use it

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CURRENCY_",
    )


currency_config = CurrencyConfig(
    _env_file=os.environ.get("GENAI_ENGINE_CURRENCY_CONFIG_PATH", ".env"),  # type: ignore[call-arg]
)
