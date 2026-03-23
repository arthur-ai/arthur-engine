from clients.currency.abc_currency_rate_provider import ABCCurrencyRateProvider
from config.currency_config import CurrencyConfig


class StaticCurrencyRateProvider(ABCCurrencyRateProvider):
    """
    Exchange rate provider that returns a single hardcoded rate from config.
    For air-gapped environments; no network calls. Redeploy to update the rate.
    """

    def __init__(self, config: CurrencyConfig) -> None:
        self._config = config

    def fetch_rates(self, base_currency: str) -> dict[str, float]:
        rates: dict[str, float] = {"USD": 1.0}
        if base_currency.upper() != "USD":
            rates[base_currency.upper()] = 1.0
        target = self._config.DEFAULT_CURRENCY.strip().upper()
        rate = self._config.CURRENCY_EXCHANGE_RATE
        if target and target != "USD" and rate is not None:
            rates[target] = rate
        return rates
