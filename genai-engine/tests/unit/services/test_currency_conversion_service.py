from unittest.mock import MagicMock, patch

import pytest

from services.currency.currency_conversion_service import (
    CurrencyConversionService,
    get_currency_conversion_service,
    initialize_currency_conversion_service,
    shutdown_currency_conversion_service,
)


@pytest.mark.unit_tests
def test_convert_usd_to_empty_cache_returns_usd() -> None:
    service = CurrencyConversionService()
    amount, currency = service.convert_usd_to(10.0, "EUR")
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_convert_usd_to_usd_returns_unconverted() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "USD")
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_convert_usd_to_eur_with_rate() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "EUR")
    assert amount == 9.2
    assert currency == "EUR"


@pytest.mark.unit_tests
def test_convert_usd_to_unknown_currency_returns_usd() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "XYZ")
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_convert_usd_to_normalizes_target_currency_case() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    amount, currency = service.convert_usd_to(10.0, "eur")
    assert amount == 9.2
    assert currency == "EUR"


@pytest.mark.unit_tests
def test_refresh_updates_cache() -> None:
    service = CurrencyConversionService()
    provider = MagicMock()
    provider.fetch_rates.return_value = {"EUR": 0.92, "GBP": 0.79}
    service._provider = provider

    service._refresh()

    assert service._rates["USD"] == 1.0
    assert service._rates["EUR"] == 0.92
    assert service._rates["GBP"] == 0.79


@pytest.mark.unit_tests
def test_refresh_on_provider_error_keeps_cache_unchanged() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    provider = MagicMock()
    provider.fetch_rates.side_effect = Exception("network error")
    service._provider = provider

    service._refresh()

    assert service._rates == {"USD": 1.0, "EUR": 0.92}


@pytest.mark.unit_tests
def test_has_rates_empty_cache() -> None:
    service = CurrencyConversionService()
    assert service.has_rates() is False
    service._rates = {"USD": 1.0, "EUR": 0.92}
    assert service.has_rates() is True


@pytest.mark.unit_tests
def test_convert_usd_to_on_exception_returns_usd() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    # Simulate a bug: invalid type could cause exception in round()
    amount, currency = service.convert_usd_to(10.0, 123)  # type: ignore[arg-type]
    assert amount == 10.0
    assert currency == "USD"


@pytest.mark.unit_tests
def test_load_rates_from_provider_populates_cache_without_thread() -> None:
    service = CurrencyConversionService()
    provider = MagicMock()
    provider.fetch_rates.return_value = {"USD": 1.0, "EUR": 0.92}
    service.load_rates_from_provider(provider)
    assert service.has_rates() is True
    assert service._rates["EUR"] == 0.92
    assert service.background_thread is None


@pytest.mark.unit_tests
def test_initialize_currency_conversion_service_static_uses_load_not_start() -> None:
    """Static provider loads rates once and does not start background thread or executor."""
    mock_config = MagicMock()
    mock_config.CURRENCY_PROVIDER = "static"
    mock_config.CURRENCY_EXCHANGE_RATE = 0.92
    mock_config.DEFAULT_CURRENCY = "EUR"
    mock_provider = MagicMock()
    mock_provider.fetch_rates.return_value = {"USD": 1.0, "EUR": 0.92}

    try:
        with (
            patch(
                "services.currency.currency_conversion_service.currency_config",
                mock_config,
            ),
            patch(
                "clients.currency.static_provider.StaticCurrencyRateProvider",
                return_value=mock_provider,
            ),
        ):
            initialize_currency_conversion_service()
        service = get_currency_conversion_service()
        assert service is not None
        assert service.background_thread is None
        assert service.has_rates()
        assert service._rates.get("EUR") == 0.92
    finally:
        shutdown_currency_conversion_service()
        assert get_currency_conversion_service() is None
