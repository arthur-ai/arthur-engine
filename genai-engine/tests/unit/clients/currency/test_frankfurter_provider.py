from unittest.mock import patch

import httpx
import pytest

from clients.currency.frankfurter_provider import FrankfurterCurrencyRateProvider


@pytest.mark.unit_tests
def test_fetch_rates_success():
    with patch("clients.currency.frankfurter_provider.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "base": "USD",
            "date": "2024-11-25",
            "rates": {"EUR": 0.92, "GBP": 0.79, "JPY": 149.5},
        }
        mock_get.return_value.raise_for_status = lambda: None

        provider = FrankfurterCurrencyRateProvider(base_url="https://api.example.com")
        rates = provider.fetch_rates("USD")

        assert rates == {"EUR": 0.92, "GBP": 0.79, "JPY": 149.5, "USD": 1.0}
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.example.com/v1/latest"
        assert call_args[1]["params"] == {"base": "USD"}


@pytest.mark.unit_tests
def test_fetch_rates_with_symbols_filter():
    with patch("clients.currency.frankfurter_provider.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "base": "USD",
            "date": "2024-11-25",
            "rates": {"EUR": 0.92, "GBP": 0.79},
        }
        mock_get.return_value.raise_for_status = lambda: None

        config = type(
            "Config",
            (),
            {
                "CURRENCY_PROVIDER_BASE_URL": "https://api.example.com",
                "SUPPORTED_CURRENCIES": ["EUR", "GBP", "JPY"],
            },
        )()
        provider = FrankfurterCurrencyRateProvider(config=config)
        rates = provider.fetch_rates("USD")

        assert "EUR" in rates and "GBP" in rates
        assert rates["USD"] == 1.0
        call_kwargs = mock_get.call_args[1]
        assert "symbols" in call_kwargs["params"]
        assert set(call_kwargs["params"]["symbols"].split(",")) == {"EUR", "GBP", "JPY"}


@pytest.mark.unit_tests
def test_fetch_rates_http_error_raises():
    with patch("clients.currency.frankfurter_provider.httpx.get") as mock_get:
        mock_get.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=httpx.Request("GET", "https://api.example.com/v1/latest"),
            response=httpx.Response(500),
        )

        provider = FrankfurterCurrencyRateProvider(base_url="https://api.example.com")
        with pytest.raises(httpx.HTTPStatusError):
            provider.fetch_rates("USD")


@pytest.mark.unit_tests
def test_fetch_rates_timeout_raises():
    with patch(
        "clients.currency.frankfurter_provider.httpx.get",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        provider = FrankfurterCurrencyRateProvider(base_url="https://api.example.com")
        with pytest.raises(httpx.TimeoutException):
            provider.fetch_rates("USD")


@pytest.mark.unit_tests
def test_fetch_rates_skips_non_numeric():
    with patch("clients.currency.frankfurter_provider.httpx.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "base": "USD",
            "date": "2024-11-25",
            "rates": {"EUR": 0.92, "INVALID": "not_a_number", "GBP": 0.79},
        }
        mock_get.return_value.raise_for_status = lambda: None

        provider = FrankfurterCurrencyRateProvider(base_url="https://api.example.com")
        rates = provider.fetch_rates("USD")

        assert rates["EUR"] == 0.92
        assert rates["GBP"] == 0.79
        assert rates["USD"] == 1.0
        assert "INVALID" not in rates
