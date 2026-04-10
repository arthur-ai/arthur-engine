"""Helpers for resolving display currency and converting USD amounts for API responses."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from config.currency_config import currency_config
from services.currency import get_currency_conversion_service

if TYPE_CHECKING:
    from schemas.internal_schemas import ApplicationConfiguration

_COST_FIELDS = ("prompt_token_cost", "completion_token_cost", "total_token_cost")

T = TypeVar("T")


def get_display_currency(application_config: ApplicationConfiguration) -> str:
    """Return the display currency code (e.g. USD, EUR). App config > env > USD."""
    raw = (
        (application_config.default_currency or "")
        or (currency_config.DEFAULT_CURRENCY or "")
        or "USD"
    )
    return raw.strip().upper()


def convert_cost_for_display(
    amount_usd: float, target_currency: str
) -> tuple[float, str]:
    """Convert a USD amount to the target currency. Returns (amount, code); on failure returns (amount_usd, 'USD')."""
    if not target_currency or target_currency.upper() == "USD":
        return (amount_usd, "USD")
    svc = get_currency_conversion_service()
    if svc is None:
        return (amount_usd, "USD")
    return svc.convert_usd_to(amount_usd, target_currency)


def apply_currency_to_token_cost_item(item: T, target_currency: str) -> tuple[str, T]:
    """Convert token cost fields to target_currency; returns (effective_currency, item)."""
    target = (target_currency or "USD").strip().upper()
    if target == "USD":
        return ("USD", item)
    update: dict[str, float] = {}
    effective_currency = target
    for field in _COST_FIELDS:
        val = getattr(item, field, None)
        if val is not None:
            converted, actual_code = convert_cost_for_display(float(val), target)
            update[field] = converted
            if actual_code == "USD":
                effective_currency = "USD"
    if not update:
        return (target, item)
    if hasattr(item, "model_copy"):
        return (effective_currency, item.model_copy(update=update))
    return (effective_currency, item)
