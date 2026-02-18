from types import SimpleNamespace

import pytest

from clients.currency.static_provider import StaticCurrencyRateProvider


def _config(
    default_currency: str = "EUR",
    exchange_rate: float = 0.92,
) -> SimpleNamespace:
    return SimpleNamespace(
        DEFAULT_CURRENCY=default_currency,
        CURRENCY_EXCHANGE_RATE=exchange_rate,
    )


@pytest.mark.unit_tests
def test_static_provider_fetch_rates_returns_usd_and_default_currency():
    config = _config(default_currency="EUR", exchange_rate=0.92)
    provider = StaticCurrencyRateProvider(config=config)
    rates = provider.fetch_rates("USD")
    assert rates == {"USD": 1.0, "EUR": 0.92}


@pytest.mark.unit_tests
def test_static_provider_fetch_rates_skips_default_when_usd():
    config = _config(default_currency="USD", exchange_rate=1.0)
    provider = StaticCurrencyRateProvider(config=config)
    rates = provider.fetch_rates("USD")
    assert rates == {"USD": 1.0}


@pytest.mark.unit_tests
def test_static_provider_fetch_rates_respects_exchange_rate():
    config = _config(default_currency="GBP", exchange_rate=0.79)
    provider = StaticCurrencyRateProvider(config=config)
    rates = provider.fetch_rates("USD")
    assert rates["GBP"] == 0.79
    assert rates["USD"] == 1.0
