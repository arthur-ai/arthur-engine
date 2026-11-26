"""Helpers for resolving the display currency. Costs stay in USD in every API
response; clients convert them for display with the rate from get_display_rate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from config.currency_config import currency_config
from services.currency import UsdRate, get_currency_conversion_service

if TYPE_CHECKING:
    from schemas.internal_schemas import ApplicationConfiguration


def get_display_currency(application_config: ApplicationConfiguration) -> str:
    """Return the display currency code (e.g. USD, EUR). App config > env > USD."""
    raw = (
        (application_config.default_currency or "")
        or (currency_config.DEFAULT_CURRENCY or "")
        or "USD"
    )
    return raw.strip().upper()


def get_display_rate(currency: str) -> Optional[UsdRate]:
    """Return the rate from USD to the display currency, or None when no rate is cached."""
    if currency == "USD":
        return UsdRate(rate=1.0, updated_at=None)
    service = get_currency_conversion_service()
    if service is None:
        return None
    return service.get_usd_rate(currency)
