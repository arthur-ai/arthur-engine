from unittest.mock import MagicMock, patch

import pytest

from services.currency.currency_conversion_service import (
    CurrencyConversionService,
    UsdRate,
    get_currency_conversion_service,
    initialize_currency_conversion_service,
    shutdown_currency_conversion_service,
)


@pytest.mark.unit_tests
def test_get_usd_rate_empty_cache_returns_none() -> None:
    service = CurrencyConversionService()
    assert service.get_usd_rate("EUR") is None


@pytest.mark.unit_tests
def test_get_usd_rate_returns_rate_and_refresh_time() -> None:
    service = CurrencyConversionService()
    provider = MagicMock()
    provider.fetch_rates.return_value = {"EUR": 0.92}
    service._provider = provider
    service._refresh()

    rate = service.get_usd_rate("EUR")

    assert rate is not None
    assert rate.rate == 0.92
    assert rate.updated_at == service._last_updated
    assert service.get_usd_rate("USD") == UsdRate(rate=1.0, updated_at=service._last_updated)


@pytest.mark.unit_tests
def test_get_usd_rate_unknown_currency_returns_none() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    assert service.get_usd_rate("XYZ") is None


@pytest.mark.unit_tests
def test_get_usd_rate_normalizes_currency_case() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    rate = service.get_usd_rate(" eur ")
    assert rate is not None
    assert rate.rate == 0.92


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
