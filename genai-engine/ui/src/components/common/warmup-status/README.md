# `warmup-status`

A status pill that surfaces the engine's background-warmup state. Mounted
once at the application root via
[`EngineWarmupStatusPill`](../../EngineWarmupStatusPill.tsx) inside
[`App.tsx`](../../../App.tsx).

## Surface

- `WarmupStatusPillView` — presentational component; takes a
  `ModelStatusResponse` and renders a chip + tooltip. Renders nothing while
  data is missing or `overall_status === "ready"`.
- `useWarmupStatus` — wraps `useQuery` with poll-until-ready logic. Honors
  the server-provided `retry_after_seconds` hint when present, otherwise
  falls back to a 2 s default. Stops polling once `overall_status === "ready"`.

Types come from the generated API client at `@/lib/api-client/api-client`
(`ModelStatusResponse`, `ModelStatusEntry`, `ModelLoadStatus`,
`OverallWarmupStatus`).

## Render rules

| `overall_status`                 | Visible | Color   | Icon             |
| -------------------------------- | ------- | ------- | ---------------- |
| `ready`                          | no      | —       | —                |
| `warming`                        | yes     | info    | spinner          |
| `partial` / `failed` / `skipped` | yes     | warning | warning triangle |

The pill also flips to the warning style when any individual model is in
`failed` or `skipped`, even if `overall_status` is still `warming`.

## Configuration

All copy strings can be overridden via the `copy` prop, which accepts a
partial `WarmupStatusPillCopy` for i18n / brand-specific phrasing.
