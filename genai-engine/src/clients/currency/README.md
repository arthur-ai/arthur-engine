# Currency rate providers

This package defines the abstraction for fetching exchange rates and provides the Frankfurter implementation. It is used by the currency conversion service to obtain USD-based rates for display in a user’s preferred currency.

## Overview

- **`ABCCurrencyRateProvider`** – Abstract base class. Implement this to plug in a new data source (e.g. another API or a test double).
- **`FrankfurterCurrencyRateProvider`** – Fetches rates from the [Frankfurter API](https://www.frankfurter.app/docs/) (default: `https://api.frankfurter.dev`). No API key required.

## Provider contract

Implementations must provide:

```python
def fetch_rates(self, base_currency: str) -> dict[str, float]:
```

- **`base_currency`** – ISO 4217 code (e.g. `"USD"`).
- **Returns** – Map of currency code → rate (amount per 1 unit of base). Example: `{"EUR": 0.92, "GBP": 0.79}` means 1 USD = 0.92 EUR.
- **Errors** – Raise on network/HTTP/parse failures so the service can keep the previous cache and fall back to USD.

## Frankfurter provider

- **Config** – Uses `config.currency_config.CurrencyConfig`:
  - `CURRENCY_PROVIDER_BASE_URL` – API base (default `https://api.frankfurter.dev`). Override for self-hosted or tests.
  - `SUPPORTED_CURRENCIES` – Optional list (e.g. `["USD", "EUR", "GBP"]`). When set, requests only those symbols; when `None`, uses all rates returned by the API.
- **API** – `GET {base_url}/v1/latest?base=USD` (and optional `symbols=...`). Response `rates` is parsed; non-numeric entries are skipped. For base USD, `USD: 1.0` is always included in the result.
- **Timeout** – HTTP request timeout (default 5 seconds). Exceptions propagate to the caller.

## Adding another provider

1. Add a new module (e.g. `other_provider.py`) and implement `ABCCurrencyRateProvider.fetch_rates(base_currency) -> dict[str, float]`.
2. In the service (or config), choose the provider (e.g. by env or feature flag) and pass it to `CurrencyConversionService.start(provider)`.

No changes are required in the service’s cache or conversion logic; it only calls `fetch_rates("USD")` and uses the returned dict.
