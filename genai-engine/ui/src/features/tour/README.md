# Tour engine (v1)

A small, opinionated tour framework for the GenAI Engine UI. v1 is a
ground-up rewrite of v0 — see `~/.cursor/plans/tour_engine_v1_*.plan.md` for
the design rationale and the dogfood issues that motivated the rebuild.

## Concepts

A **tour** is built from `createTour({ config, plugins })`:

- The **config** is a list of sections; each section has an optional
  introduction and a list of steps. Steps point at a **target** (selector,
  React ref, callback, or hook-resolved element), declare one or more
  **advance triggers** (manual / click / visible / action), and may declare
  a **prepare** hook, a **skipWhen** predicate, and route metadata.
- The **engine** owns a deterministic state machine
  (`idle → intro → step* → completed | skipped | dismissed`) and a typed
  mitt event bus. Most consumer code never reaches into the engine — it
  consumes state through React hooks.
- **Plugins** install side-effects on the engine (persistence, analytics,
  preparation registries, custom highlight renderers). Each plugin gets a
  `TourPluginContext` with the engine store, the bus, and registration
  helpers.
- **Widgets** are ordinary consumer-authored React components mounted
  inside `<TourHost>`. The library ships no “DefaultTour”; consumers
  compose the UI by combining the primitives (`Spotlight`,
  `BackdropBlocker`, `PopoverAnchor`, `TargetTracker`, `TourPortal`) with
  their own panels and modals.

## Public surface

```ts
import {
  createTour,
  TourProvider,
  TourHost,
  useTour, // { state, config, actions, activeStep, activeSection }
  useTourState, // current TourState
  useTourStore, // raw Zustand slice selector
  useTourEvent, // bus subscription
  useTourAction, // (name) => engine.emitAction(name)
  useTourLayer, // z-index slice
  useRegisterQueryHook,
  useRegisterPreparation,
  Spotlight,
  BackdropBlocker,
  PopoverAnchor,
  TargetTracker,
  TourPortal,
  withTourActive,
  withTourStep,
  createTourStatePlugin,
  createAnalyticsPlugin,
  createPreparationPlugin,
  createHighlightsPlugin,
} from "@/features/tour";
```

## Composing a tour

```tsx
const engine = createTour({
  config: buildMyConfig(),
  plugins: [createTourStatePlugin({ storageKey: "my-tour" })],
});

<TourProvider tour={engine} navigator={navigator}>
  <TourHost>
    <MyIntroWidget />
    <MySpotlightWidget />
    <MyChecklistWidget />
    <MyResumeFabWidget />
  </TourHost>
</TourProvider>;
```

Each widget is a small React component that reads engine state through
`useTour*` hooks and dispatches actions back to the engine. No widget is
provided by the library; the `features/task-tour` package contains the
canonical example.

## Targeting

Steps declare a `TargetSpec`:

- `{ kind: "selector", selector: string }` — `document.querySelector(...)`.
- `{ kind: "element", resolve }` — bring-your-own resolver.
- `{ kind: "ref", ref }` — React ref read at step-enter time.
- `{ kind: "queryHook", hookId }` — defers to a resolver registered via
  `useRegisterQueryHook(hookId, resolver)`. Use this when a `data-tour-id`
  can't reliably propagate through a third-party component (the
  `traces.open-trace` / `traces.review-spans` flow in `task-tour` is the
  canonical example).

The engine resolves the target synchronously first; if missing and the
step declares `awaitTarget: { timeoutMs }`, it falls back to a
`MutationObserver`-driven async resolution.

## Actions

v0 emitted advance events through `document.dispatchEvent`. v1 replaces
that with a typed action channel:

```ts
const emit = useTourAction();
emit("trace-opened");
```

A step's `advanceOn: { type: "action", name: "trace-opened" }` listens on
the engine bus for matching actions. `engine.emitAction(name)` does the
same from outside React.

## Preparation hooks

For steps where the target depends on app state that needs to be primed
first (e.g. open a drawer, set pagination, fetch a record), declare
`prepare: { key }` on the step and register a matching hook:

```ts
useRegisterPreparation("traces.open-drawer", async ({ stepContext }) => {
  await openFirstTraceDrawer();
  return { ready: true };
});
```

The engine mounts the hook (via `<PreparationRunner />` inside `TourHost`)
right after navigation, waits for `{ ready: true }`, and only then
resolves the target.

## Plugins

- `createTourStatePlugin({ storageKey })` — single-record persistence +
  completed-set progress, with `localStorage` mirror and cross-tab
  `storage`-event sync. Exposes a Zustand store consumed via
  `useTourPluginStore(plugin, selector)`.
- `createPreparationPlugin()` — Zustand-backed registry of preparation
  hooks (when you want plugin-driven prep instead of inline
  `useRegisterPreparation`).
- `createHighlightsPlugin({ renderers })` — registers custom highlight
  renderers.
- `createAnalyticsPlugin({ track, prefix, include })` — forwards bus
  events to the supplied tracker.

## Migrating from v0

- `tourEvents.ts` / `tourEventNames.ts` → typed action channel
  (`useTourAction`, `engine.emitAction`).
- `createPersistencePlugin` + `createChecklistProgressPlugin` →
  `createTourStatePlugin` (one store, one storage record).
- `DefaultTour` / `DefaultIntroDialog` / `DefaultStepPopover` removed.
  Consumers author their own widget set inside `<TourHost>`.
- `introductionPending` flag removed. The engine state machine has a
  first-class `intro` status (`status: "intro" | "step" | ...`).
- Stub-step placeholder removed. Intro-only sections have
  `steps: []` and advance through `acknowledgeIntroduction()`.
- `event` trigger removed. Use `{ type: "action", name }` instead.
