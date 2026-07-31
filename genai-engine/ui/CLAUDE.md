# GenAI Engine UI

React 19 + TypeScript + Vite SPA for the GenAI Engine (tasks, prompts, datasets, traces). MUI is the component library; TanStack Query/Form/Table for data, Zustand for client state, nuqs for URL state, Zod v4 for validation, Yarn 4.

## Commands

```bash
yarn dev                  # dev server
yarn check                # type-check + lint + format:check — required before committing, CI enforced
yarn format               # auto-fix formatting
yarn test:run             # vitest
yarn generate-api:clean   # regenerate API client after backend OpenAPI spec changes
```

## API client & data fetching

- `src/lib/api-client/` is generated from the backend OpenAPI spec — never hand-edit it; regenerate. Import backend types from it instead of re-declaring them (derive with `Pick<>` etc.).
- Fetch with `useApiQuery` and mutate with `useApiMutation` (`src/hooks/`) — the mutation hook takes `invalidateQueries` and handles cache invalidation. Query keys come from the central `queryKeys` object in [src/lib/queryKeys.ts](src/lib/queryKeys.ts).
- Never fetch in a raw `useEffect`; more generally, prefer values derived during render over effects and extra state.

## Forms (TanStack Form + Zod v4)

Custom typed wrappers live in [src/components/traces/components/filtering/hooks/form.tsx](src/components/traces/components/filtering/hooks/form.tsx): `useAppForm(options)` creates the form, `form.AppField name="path"` renders typed fields, `form.Subscribe` / `useStore(form.store, selector)` for reactive reads.

- Prefer `withForm({ ...formOpts, props?, render })` over `withFieldGroup` for sub-components that display validation errors — `withFieldGroup` error types resolve to `never` (no `.message`). Use named render functions to satisfy ESLint hook rules.
- Zod v4 custom messages use `{ error: "..." }`, not `{ message: "..." }`; target a nested field on `.refine()` with `path: ["field"]`.
- Form-level validators (`parseValuesWithSchema`) propagate field errors to `field.state.meta.errors`, but `resetField()` does NOT clear them — clear explicitly:
  ```tsx
  form.setFieldMeta(path, (prev) => ({ ...prev, errorMap: { ...prev.errorMap, onSubmit: undefined } }));
  ```
- `form.state.isDirty` is persistent — stays true once any field changed, even if reverted.
- Multi-step forms track the step in a `section` field: forward navigation uses `form.handleSubmit()` (validates), back sets `form.setFieldValue("section", prev)` (skips validation).

## MUI styling (mandatory)

- Always use MUI components — never plain HTML (`<button>`, `<table>`, custom modals, `<div>` layout) when an MUI equivalent exists, and don't add UI libraries that duplicate MUI.
- Style via the `sx` prop with theme color tokens (`primary.main`, `text.secondary`, `error.50`, …) — no inline `style={{}}`, no raw hex/rgb values.
- Tailwind is only for supplementary layout utilities (flex, spacing); never for colors or typography.
- Conventions: buttons `variant="contained"`/`outlined`/`text` for primary/secondary/tertiary; `variant="filled"` TextFields; icons from `@mui/icons-material`; `<Alert>` for inline messages, notistack's `enqueueSnackbar` for toasts.

## Misc gotchas

- Currency display: `useDisplaySettings()` provides `defaultCurrency` (from `GET /api/v2/display-settings`; backend default set by the `CURRENCY_DEFAULT_CURRENCY` env var). Format with `formatCurrency(amount, defaultCurrency)` from `@/utils/formatters`.
- The auth token lives in localStorage, managed by `AuthContext`.
