from unittest.mock import MagicMock

import pytest

from services.currency.currency_conversion_service import CurrencyConversionService


@pytest.mark.unit_tests
def test_convert_usd_to_empty_cache_returns_usd():
    service = CurrencyConversionService()
    amount, currency = service.convert_usd_to(10.0, "EUR")
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_convert_usd_to_usd_returns_unconverted():
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "USD")
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_convert_usd_to_eur_with_rate():
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "EUR")
    assert amount == 9.2
    assert currency == "EUR"


@pytest.mark.unit_tests
def test_convert_usd_to_unknown_currency_returns_usd():
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "XYZ")
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_convert_usd_to_normalizes_target_currency_case():
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "eur")
    assert amount == 9.2
    assert currency == "EUR"


@pytest.mark.unit_tests
def test_refresh_updates_cache():
    service = CurrencyConversionService()
    provider = MagicMock()
    provider.fetch_rates.return_value = {"EUR": 0.92, "GBP": 0.79}
    service._provider = provider

    service._refresh()

    assert service._rates["USD"] == 1.0
    assert service._rates["EUR"] == 0.92
    assert service._rates["GBP"] == 0.79


@pytest.mark.unit_tests
def test_refresh_on_provider_error_keeps_cache_unchanged():
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    provider = MagicMock()
    provider.fetch_rates.side_effect = Exception("network error")
    service._provider = provider

    service._refresh()

    assert service._rates == {"USD": 1.0, "EUR": 0.92}


@pytest.mark.unit_tests
def test_has_rates_empty_cache():
    service = CurrencyConversionService()
    assert service.has_rates() is False
    service._rates = {"USD": 1.0, "EUR": 0.92}
    assert service.has_rates() is True


@pytest.mark.unit_tests
def test_convert_usd_to_on_exception_returns_usd():
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    # Simulate a bug: invalid type could cause exception in round()
    amount, currency = service.convert_usd_to(10.0, 123)  # type: ignore[arg-type]
    assert amount == 10.0
    assert currency == "USD"
