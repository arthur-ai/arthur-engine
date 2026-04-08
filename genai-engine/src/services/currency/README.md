# Currency conversion service

This package provides the in-app currency conversion layer: it keeps an in-memory cache of USD exchange rates, refreshes them on a schedule, and exposes a single method to convert USD amounts to a target currency. It is intended for displaying costs (e.g. AI API usage) in the user’s preferred currency.

## Overview

- **`CurrencyConversionService`** – Holds a thread-safe cache of rates (USD → other currencies). When using the Frankfurter provider, a background thread refreshes on a schedule; when using the static provider, rates are loaded once and no thread runs. Exposes `convert_usd_to(amount_usd, target_currency)`.
- **Lifecycle** – The service is a singleton (global `CURRENCY_CONVERSION_SERVICE`). The app starts or loads it in FastAPI lifespan via `initialize_currency_conversion_service()` and stops it via `shutdown_currency_conversion_service()` (which calls `stop(timeout=30)` and sets the singleton to `None`). The service subclasses `BaseQueueService` (same as the continuous-eval and agent-polling services); for the static provider no background thread or executor is started, so `stop()` is a no-op.

## Behavior

### Refresh schedule

- **Frankfurter** – A background thread runs: one fetch immediately, then refreshes at **00:00, 06:00, 12:00, 18:00 UTC** every 6 hours.
- **Static** – When `CURRENCY_PROVIDER=static`, rates are loaded once via `load_rates_from_provider()` and **no thread is started**. For air-gapped environments; redeploy to update the rate.
- **Provider** – Chosen by `currency_config.CURRENCY_PROVIDER` (`frankfurter` or `static`). See `src/clients/currency/README.md` for the provider contract.

### Conversion

- **`convert_usd_to(amount_usd: float, target_currency: str) -> tuple[float, str]`**
  Returns `(converted_amount, currency_code)`.
- **Fallback to USD** – If the target is `"USD"`, the rate is missing, or any exception occurs, the method returns `(amount_usd, "USD")` (unconverted). Callers can treat this as “show in USD.”
- **Precision** – Converted amounts are rounded to 6 decimal places.

### Readiness

- **`has_rates() -> bool`** – Returns whether the cache has at least one rate (e.g. after the first successful refresh). Useful for scripts or tests that wait until the service is ready before calling `convert_usd_to`.

### Thread safety

- The cache is protected by an `RLock`. `convert_usd_to` and `has_rates` are safe to call from any thread while the background thread updates the cache.

## Usage in the app

- **Dependency** – Use `get_currency_conversion_service()` (e.g. via FastAPI `Depends`) to get the singleton. It returns `None` until `initialize_currency_conversion_service()` has been called and is set back to `None` after `shutdown_currency_conversion_service()`. Do not call `start()` in the getter; the thread is started only in lifespan.
- **Lifespan** – In `server.py`, after other init, call `initialize_currency_conversion_service()`. Before the lifespan context exits, call `shutdown_currency_conversion_service()` so the background thread exits cleanly.

## Configuration

See `config.currency_config`. Env prefix: `CURRENCY_`. Environment variable `CURRENCY_DEFAULT_CURRENCY` (e.g. in `.env` or `docker-compose.yml`) populates `DEFAULT_CURRENCY`; both default to `USD`.

- **`DEFAULT_CURRENCY`** – App-wide display currency (e.g. `EUR`). Used by API/display layer when no per-application override is set. The conversion service does not read it; callers pass the target when converting: `convert_usd_to(amount_usd, currency_config.DEFAULT_CURRENCY)`.
- **`CURRENCY_PROVIDER`** – `frankfurter` (default) or `static`. When `static`, no external calls and no background thread.
- **`CURRENCY_EXCHANGE_RATE`** – Required when provider is `static`: rate from USD to `DEFAULT_CURRENCY` (e.g. `0.92` for EUR).
- **`CURRENCY_PROVIDER_API_KEY`** – Optional; Frankfurter does not use it; other providers can.
- **`CURRENCY_PROVIDER_BASE_URL`**, **`SUPPORTED_CURRENCIES`** – For Frankfurter (see clients/currency README).

## Standalone test script

To run the service once (start, wait for rates, convert, print, shutdown) from the command line:

```bash
cd genai-engine
PYTHONPATH=src uv run python scripts/test_currency_conversion_standalone.py [amount] [currency]
```

Example: `... 25 EUR` converts 25 USD to EUR and prints the result. The script polls `has_rates()` until the first fetch completes or a timeout is reached.
