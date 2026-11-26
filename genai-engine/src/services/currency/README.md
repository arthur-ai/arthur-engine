# Currency conversion service

This package keeps an in-memory cache of USD exchange rates and refreshes it on a schedule. Costs stay in USD in every API response; `GET /api/v2/display-settings` returns the rate to the display currency, and clients convert costs for display with it.

## Overview

- **`CurrencyConversionService`** – Holds a thread-safe cache of rates (USD → other currencies). When using the Frankfurter provider, a background thread refreshes on a schedule; when using the static provider, rates are loaded once and no thread runs. Exposes `get_usd_rate(currency)`.
- **Lifecycle** – The service is a singleton (global `CURRENCY_CONVERSION_SERVICE`). The app starts or loads it in FastAPI lifespan via `initialize_currency_conversion_service()` and stops it via `shutdown_currency_conversion_service()` (which calls `stop(timeout=30)` and sets the singleton to `None`). The service subclasses `BaseQueueService` (same as the continuous-eval and agent-polling services); for the static provider no background thread or executor is started, so `stop()` is a no-op.

## Behavior

### Refresh schedule

- **Frankfurter** – A background thread runs: one fetch immediately, then refreshes at **00:00, 06:00, 12:00, 18:00 UTC** every 6 hours.
- **Static** – When `CURRENCY_PROVIDER=static`, rates are loaded once via `load_rates_from_provider()` and **no thread is started**. For air-gapped environments; redeploy to update the rate.
- **Provider** – Chosen by `currency_config.CURRENCY_PROVIDER` (`frankfurter` or `static`). See `src/clients/currency/README.md` for the provider contract.

### Rates

- **`get_usd_rate(currency: str) -> Optional[UsdRate]`**
  Returns the units of `currency` one USD buys and when the cache was refreshed, or `None` when the currency has no cached rate. Clients then show costs in USD.

### Readiness

- **`has_rates() -> bool`** – Returns whether the cache has at least one rate (e.g. after the first successful refresh). Useful for tests that wait until the service is ready.

### Thread safety

- The cache is protected by an `RLock`. `get_usd_rate` and `has_rates` are safe to call from any thread while the background thread updates the cache.

## Usage in the app

- **Dependency** – Use `get_currency_conversion_service()` (e.g. via FastAPI `Depends`) to get the singleton. It returns `None` until `initialize_currency_conversion_service()` has been called and is set back to `None` after `shutdown_currency_conversion_service()`. Do not call `start()` in the getter; the thread is started only in lifespan.
- **Lifespan** – In `server.py`, after other init, call `initialize_currency_conversion_service()`. Before the lifespan context exits, call `shutdown_currency_conversion_service()` so the background thread exits cleanly.

## Configuration

See `config.currency_config`. Env prefix: `CURRENCY_`. Environment variable `CURRENCY_DEFAULT_CURRENCY` (e.g. in `.env` or `docker-compose.yml`) populates `DEFAULT_CURRENCY`; both default to `USD`.

- **`DEFAULT_CURRENCY`** – App-wide display currency (e.g. `EUR`). Used by API/display layer when no per-application override is set. The service does not read it; display settings look up its rate with `get_usd_rate`.
- **`CURRENCY_PROVIDER`** – `frankfurter` (default) or `static`. When `static`, no external calls and no background thread.
- **`CURRENCY_EXCHANGE_RATE`** – Required when provider is `static`: rate from USD to `DEFAULT_CURRENCY` (e.g. `0.92` for EUR).
- **`CURRENCY_PROVIDER_API_KEY`** – Optional; Frankfurter does not use it; other providers can.
- **`CURRENCY_PROVIDER_BASE_URL`**, **`SUPPORTED_CURRENCIES`** – For Frankfurter (see clients/currency README).
