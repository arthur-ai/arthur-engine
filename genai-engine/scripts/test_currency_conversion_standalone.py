#!/usr/bin/env python3
"""
Standalone script to run the currency conversion service: start service, fetch
rates from the configured provider (Frankfurter), convert an amount, print
result, then shut down.

Usage (from genai-engine directory):
  PYTHONPATH=src poetry run python scripts/test_currency_conversion_standalone.py
  PYTHONPATH=src poetry run python scripts/test_currency_conversion_standalone.py 25 EUR

Exits 0 on success, 1 if conversion fell back to USD when a non-USD currency was requested.
"""

import argparse
import os
import sys
import time

# Ensure src is on path when run as script from genai-engine (before project imports)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_genai_root = os.path.abspath(os.path.join(_script_dir, ".."))
_src = os.path.join(_genai_root, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)

from clients.currency.frankfurter_provider import FrankfurterCurrencyRateProvider
from config.currency_config import currency_config
from services.currency.currency_conversion_service import CurrencyConversionService

POLL_INTERVAL_SECONDS = 0.5
WAIT_FOR_RATES_TIMEOUT_SECONDS = 10.0


def wait_for_rates(service: CurrencyConversionService) -> bool:
    """Poll until service.has_rates() is True or timeout. Return True if rates loaded."""
    deadline = time.monotonic() + WAIT_FOR_RATES_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if service.has_rates():
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run currency conversion service once: fetch rates, convert, print, exit."
    )
    parser.add_argument(
        "amount",
        type=float,
        nargs="?",
        default=10.0,
        help="Amount in USD to convert (default: 10.0)",
    )
    parser.add_argument(
        "currency",
        type=str,
        nargs="?",
        default="EUR",
        help="Target currency code (default: EUR)",
    )
    args = parser.parse_args()
    amount_usd = args.amount
    target_currency = (args.currency or "EUR").strip().upper()

    service = CurrencyConversionService()
    provider = FrankfurterCurrencyRateProvider(config=currency_config)
    service.start(provider)

    if not wait_for_rates(service):
        print(
            "Timed out waiting for rates from provider; converting will return USD.",
            file=sys.stderr,
        )

    converted, currency = service.convert_usd_to(amount_usd, target_currency)
    service.shutdown(timeout=10)

    print(f"{amount_usd} USD => {converted} {currency}")
    if target_currency != "USD" and currency == "USD":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
