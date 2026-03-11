# Contexts

React Context providers for app-wide state. This document covers display settings and how they relate to the backend currency conversion service.

## DisplaySettingsContext

**Purpose:** Provides the current display settings from the API, including the default currency used for formatting costs (e.g. AI usage) in the UI.

- **API:** Fetches `GET /api/v2/display-settings`, which returns `{ default_currency: string }`.
- **Hook:** `useDisplaySettings()` returns `{ defaultCurrency, isLoading }`. Must be used inside `DisplaySettingsProvider`.
- **Default:** If the API is pending or fails, `defaultCurrency` falls back to `"USD"`.
- **Caching:** Display settings are cached with a 5-minute stale time.

### Default currency and the backend

- The backend’s default currency is configured via **`CURRENCY_DEFAULT_CURRENCY`** in `.env` or Docker (e.g. `CURRENCY_DEFAULT_CURRENCY=USD`). That populates `currency_config.DEFAULT_CURRENCY` (see `genai-engine/src/config/currency_config.py`).
- The **currency conversion service** on the backend always converts **from USD** to a target currency. It does **not** read the default-currency config; it only converts to whatever target callers pass. When no target or an invalid target is given, it returns the amount in USD.
- The **display settings API** returns the app-wide default currency (from config or per-application overrides). The UI uses this value so that cost amounts are shown in the user’s preferred currency (e.g. USD, EUR) without the frontend needing to know how that default was chosen.

So: `.env` / Docker set the default **display** currency; the conversion service is agnostic and only converts USD → target; the UI gets the effective default from the display-settings endpoint and uses it for formatting.

### Using default currency in the UI

Use `useDisplaySettings()` to get `defaultCurrency`, then pass it to the currency formatter:

```tsx
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { formatCurrency } from "@/utils/formatters";

// In your component:
const { defaultCurrency } = useDisplaySettings();
// ...
formatCurrency(metrics?.totalCost ?? 0, defaultCurrency);
```

See `src/components/TaskOverview.tsx` for an example. The `formatCurrency(amount, currencyCode)` helper in `src/utils/formatters.ts` uses `Intl.NumberFormat` with the given currency code (defaulting to `"USD"` if omitted).
