# Contexts – agent context

- **DisplaySettingsContext:** Provides `defaultCurrency` from the backend display-settings API (`GET /api/v2/display-settings` → `default_currency`). Backend default is set by `CURRENCY_DEFAULT_CURRENCY` (env); the backend conversion service converts USD → target and does not read default currency.
- **Usage:** Call `useDisplaySettings()` (inside `DisplaySettingsProvider`) to get `defaultCurrency`; use `formatCurrency(amount, defaultCurrency)` from `@/utils/formatters` for cost display.
- **Other contexts:** `AuthContext`, `TaskContext`, `DatasetContext` – see their files and the repo root AGENTS.md for patterns.
