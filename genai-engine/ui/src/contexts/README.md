# Contexts

React Context providers for app-wide state. This document covers display settings and how they relate to the backend currency conversion service.

## DisplaySettingsContext

**Purpose:** Provides the current display settings from the API, including the currency costs (e.g. AI usage) are shown in.

- **API:** Fetches `GET /api/v2/display-settings`, which returns `default_currency`, `usd_exchange_rate` (units of that currency one USD buys) and `exchange_rate_updated_at`.
- **Hook:** `useDisplaySettings()` returns `{ currency, isLoading, ... }`, where `currency` is a `DisplayCurrency` (`{ code, usdRate, rateDate }`) from `@arthur/shared-components`. Must be used inside `DisplaySettingsProvider`.
- **Default:** If the API is pending or fails, or returns no rate, `currency` is USD with a rate of 1.

### Costs are USD; conversion happens for display

- Every cost in the engine's API responses is in USD, whatever the configured currency.
- The display currency is configured via **`CURRENCY_DEFAULT_CURRENCY`** in `.env` or Docker (e.g. `CURRENCY_DEFAULT_CURRENCY=EUR`), or per application. The display settings API returns it together with the current rate from USD, which the backend's currency conversion service fetches and caches.
- The UI converts USD costs with that rate only when it formats them, so data never mixes currencies.

### Showing a cost in the UI

Pass the USD amount and the display currency to `formatCost` from `@arthur/shared-components`, which converts and formats it:

```tsx
import { formatCost } from "@arthur/shared-components";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";

const { currency } = useDisplaySettings();
// ...
formatCost(metrics?.totalCost ?? 0, currency);
```

`formatCost` shows small amounts with three significant digits, larger ones with the currency's usual decimals, zero as zero, and `null`/`undefined` as "—" (unknown, not free). See `src/components/TaskOverview.tsx` for an example.
