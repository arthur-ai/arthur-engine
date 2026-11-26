from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from services.currency import CurrencyConversionService, UsdRate
from utils.currency_display import get_display_rate


@pytest.mark.unit_tests
def test_usd_rate_is_one_without_a_service() -> None:
    with patch(
        "utils.currency_display.get_currency_conversion_service",
        return_value=None,
    ):
        assert get_display_rate("USD") == UsdRate(rate=1.0, updated_at=None)


@pytest.mark.unit_tests
def test_rate_comes_from_the_conversion_service() -> None:
    service = CurrencyConversionService()
    service._rates = {"USD": 1.0, "EUR": 0.92}
    service._last_updated = datetime(2026, 11, 26, 6, tzinfo=timezone.utc)
    with patch(
        "utils.currency_display.get_currency_conversion_service",
        return_value=service,
    ):
        assert get_display_rate("EUR") == UsdRate(
            rate=0.92,
            updated_at=datetime(2026, 11, 26, 6, tzinfo=timezone.utc),
        )


@pytest.mark.unit_tests
def test_no_rate_when_the_service_has_none() -> None:
    with patch(
        "utils.currency_display.get_currency_conversion_service",
        return_value=None,
    ):
        assert get_display_rate("EUR") is None
    with patch(
        "utils.currency_display.get_currency_conversion_service",
        return_value=CurrencyConversionService(),
    ):
        assert get_display_rate("EUR") is None
