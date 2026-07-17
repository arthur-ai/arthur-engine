# Analytics (Amplitude) – agent context

All product analytics flow through this module. Only `client.ts`, `session-replay.ts`, and `experiments.ts` may import `@amplitude/*`; everything else imports from `@/services/analytics`.

## Adding an event

1. Add a key to the matching domain interface under `events/` (e.g. `events/datasets.ts`, `events/onboarding.ts`, `events/task-tour.ts`). The key is the **wire name** sent to Amplitude verbatim — never rename an existing one or you break existing charts/cohorts.
2. The interface is merged into `AnalyticsEvents` in `events/index.ts`, so `track("domain/action", props)` is now type-checked (properties required/forbidden to match the declared shape).
3. Call `track(...)` at the call site. Use `trackDynamic(name, props)` only for runtime-generated names (e.g. the tour bus stream).

## Amplitude SDK reference

When wiring SDK behavior (init options, `Identify`, user properties, Session Replay setup/order), consult the **`user-amplitude-docs` MCP server** for the current, authoritative API rather than guessing. It serves Amplitude's documentation; it does not know this project's own event taxonomy (that lives in `events/`).

## Demo Lifecycle → HubSpot wiring

The "Evals 101" task tour feeds the demo nurture playbook. Its lifecycle events are emitted by the shared tour engine: `useTaskTourEngine.ts` registers `createAnalyticsPlugin({ track: trackDynamic, prefix: "task-tour" })` with **no `include` filter**, so every tour-bus event is forwarded to Amplitude as `task-tour.<event>`. Tour ID is `task-tour-evals-101`.

Signals the playbook paths key off:

| Path                     | Signal                                                                    |
| ------------------------ | ------------------------------------------------------------------------- |
| P0 never started         | `onboarding/landing_viewed` / `Login`, no `task-tour.tour:start`          |
| P1 abandoned pre-evals   | `task-tour.section:enter` `sectionIndex` 0-1, no `sectionIndex` 2         |
| P2 abandoned mid/late    | `sectionIndex` 2-5, no `sectionIndex` 6 / no `task-tour.tour:end`         |
| P3 completed             | `task-tour.tour:end` or `sectionIndex` 6                                  |
| P4 completed + activated | P3 + `product_activated` (phase 2, see below)                             |
| P5 errored/stuck         | `task-tour.render_error`, `tour/error`, `task-tour.occlusion-unrecovered` |
| P6 dismissed             | `task-tour.tour:dismiss`                                                  |

`section:enter` carries `{ tourId, sectionId, sectionIndex }`. Section index → id: `0 intro`, `1 agent`, `2 evals`, `3 traces`, `4 datasets`, `5 prompts`, `6 deploy`.

P5 error events are app-side: `task-tour.render_error` from the `ErrorBoundary` in `TaskTour.tsx` (render crash), `tour/error` from the `createTour` try/catch in `useTaskTourEngine.ts` (engine init). Async engine failures (prepare/navigation/trigger/target/runtime) are NOT yet captured — that needs a `tour:error` bus event in `@arthur/shared-components` (tracked follow-up).

## Acquisition / UTM attribution (playbook path P0)

Channel attribution ("which content channel drove the signup") is captured by the Amplitude Browser SDK's built-in marketing attribution, enabled via `autocapture.attribution` in `initAnalytics` (`client.ts`). It sets `utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content` (plus first-touch `initial_utm_*`, `referrer`, `referring_domain`, and click IDs) as **sticky user properties**, so they attach to every downstream event including `onboarding/form_submitted`. This is distinct from the self-reported `attribution` form field, which is a user's manual "how did you hear about us" answer, not an automated referral source. All other autocapture surfaces (page views, sessions, form interactions, etc.) are intentionally left off to keep the event stream low-noise.

## Task creation milestone ("create their own task")

`task/created` (`events/tasks.ts`) fires when a user creates their own task via `CreateTaskForm`. It is the "create their own task" success milestone and is **not** the same as `dataset/created` (which requires a task but tracks a later, different action). The demo onboarding task is provisioned server-side (`signup.task_id` in `onboarding-page`) and never fires `task/created`, so this event cleanly isolates user-initiated task creation.

## Identity (playbook "prerequisite zero")

Email is attached as an Amplitude user property **only on the signup form path** (`OnboardingPage` calls `identify(data.email, ...)`). The **API-key login path** (`AuthContext.login`) attaches no email: `MeResponse` carries only `user_id` (the API key id), never an email. Events from returning API-key sessions therefore cannot be matched to a HubSpot contact by email until identity is sourced another way.

## product_activated (phase 2)

`markProductActivated(reason)` (`client.ts`) sets the `product_activated` user property for the P4 cohort. It is a **stub**: the name is fixed so the cohort can be authored, but it is not yet wired to a call site. Invoke it once the app can detect a user's own agent trace, a self-hosted engine, or an experiment on their own data.
