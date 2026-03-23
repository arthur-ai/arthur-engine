import logging
from typing import Optional

import httpx

from clients.currency.abc_currency_rate_provider import ABCCurrencyRateProvider
from config.currency_config import CurrencyConfig

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5.0


class FrankfurterCurrencyRateProvider(ABCCurrencyRateProvider):
    """Exchange rate provider using the Frankfurter API (api.frankfurter.dev)."""

    def __init__(
        self,
        config: Optional[CurrencyConfig] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._config = config
        self._base_url = (
            base_url or (config.CURRENCY_PROVIDER_BASE_URL if config else None)
        ) or "https://api.frankfurter.dev"
        self._timeout = timeout_seconds

    def fetch_rates(self, base_currency: str) -> dict[str, float]:
        url = f"{self._base_url.rstrip('/')}/v1/latest"
        params: dict[str, str] = {"base": base_currency.upper()}
        if self._config and self._config.SUPPORTED_CURRENCIES:
            symbols = [
                c
                for c in self._config.SUPPORTED_CURRENCIES
                if c != base_currency.upper()
            ]
            if symbols:
                params["symbols"] = ",".join(symbols)

        response = httpx.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        data = response.json()

        rates = dict(data.get("rates", {}))
        for key in list(rates.keys()):
            try:
                rates[key] = float(rates[key])
            except (TypeError, ValueError):
                logger.warning("Skipping non-numeric rate for %s", key)
                del rates[key]

        if base_currency.upper() == "USD":
            rates["USD"] = 1.0
        return rates
