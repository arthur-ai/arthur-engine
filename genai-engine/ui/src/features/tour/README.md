# Tour

A driver.js-like guided tour library. Ships a headless engine, React bindings,
a React Router 7 navigator adapter, a default MUI UI, and a vendor-agnostic
analytics plugin.

## Layers

```
features/tour/
├── core/                       # Pure, no React
│   ├── types.ts                # All public types
│   ├── events.ts               # mitt-based event bus (typed)
│   ├── targets.ts              # sync / async target resolution
│   ├── routes.ts               # default resolveRoute + matches
│   ├── triggers/               # registry + manual / click / visible / event
│   ├── engine.ts               # state machine + lifecycle pipeline
│   └── createTour.ts           # public factory
├── react/
│   ├── TourProvider.tsx
│   ├── useTour.ts              # state + actions (useSyncExternalStore)
│   ├── useTourEvent.ts         # subscribe to a single bus event
│   ├── adapters/reactRouter.ts # useReactRouterNavigator()
│   └── primitives/             # TourPortal, Spotlight, PopoverAnchor, TargetTracker
├── ui/                         # Default MUI UI
│   ├── DefaultTour.tsx         # drop-in composition (portal + tracker + spotlight + popover)
│   ├── DefaultIntroDialog.tsx  # section introduction modal
│   └── DefaultStepPopover.tsx  # step popover body (Skip / Back / Next-Done)
├── plugins/
│   └── createAnalyticsPlugin.ts # forward all bus events to a caller-supplied tracker
└── index.ts                    # barrel
```

## Usage

```tsx
import { createTour, DefaultTour, TourProvider, useReactRouterNavigator } from "@/features/tour";

const tour = createTour({
  config: {
    id: "main-onboarding",
    sections: [
      {
        id: "analyze",
        title: "Analyze",
        route: "/analyze",
        steps: [
          {
            id: "filters",
            target: { kind: "selector", selector: '[data-tour-id="filters"]' },
            content: "Pick a date range here.",
            advanceOn: { type: "click" },
          },
        ],
      },
      {
        id: "observe",
        title: "Observe",
        introduction: { title: "Now let's look at observability" },
        route: { path: "/observe", search: { range: "24h" } },
        steps: [
          {
            id: "chart",
            target: { kind: "selector", selector: '[data-tour-id="observe-chart"]' },
            awaitTarget: { timeoutMs: 3000 },
            content: "This is your live throughput.",
          },
          {
            id: "task-detail",
            route: { path: "/tasks/:taskId", params: { taskId: "abc-123" } },
            target: { kind: "selector", selector: '[data-tour-id="task-header"]' },
            content: "Drill into a task to see its rules.",
          },
        ],
      },
    ],
  },
});

function TourBridge({ children }: { children: React.ReactNode }) {
  const navigator = useReactRouterNavigator();
  return (
    <TourProvider tour={tour} navigator={navigator}>
      {children}
      <DefaultTour />
    </TourProvider>
  );
}
```

`<DefaultTour />` is a drop-in that composes `TourPortal`, `TargetTracker`,
`Spotlight`, `PopoverAnchor`, `DefaultIntroDialog`, and `DefaultStepPopover`. It
returns `null` when the tour isn't running, so mount it once at the app root.

If you need a custom scene, compose the headless primitives yourself — see the
`ui/DefaultTour.tsx` source for the canonical pattern.

## Default UI building blocks

The components under `ui/` are exported individually so you can mix-and-match:

- `<DefaultIntroDialog open section actions />` — the section introduction modal.
- `<DefaultStepPopover activeStep actions />` — the popover body. Drop this inside your own `PopoverAnchor` if you want a custom backdrop or z-index.

All three components use MUI theme tokens and the `sx` prop; no raw colors.

## Analytics

`createAnalyticsPlugin` forwards every event on the bus to a caller-supplied
`track` function. It stays decoupled from any specific vendor — wire it up at
the call site with whatever tracker the app uses:

```tsx
import { createAnalyticsPlugin, createTour } from "@/features/tour";
import { track } from "@/services/amplitude";

const tour = createTour({
  config: {
    /* ... */
  },
  plugins: [createAnalyticsPlugin({ track, prefix: "tour" })],
});
```

Every bus event becomes a tracked event named `${prefix}.${eventName}` (e.g.
`tour.step:enter`, `tour.section:skip`). The full payload is forwarded as the
properties object.

## Routing

The engine is router-agnostic. A `TourNavigator` adapter is plugged in via
`<TourProvider navigator={...}>`. The bundled adapter is
`useReactRouterNavigator()`; other routers only need to implement:

```ts
type TourNavigator = {
  getLocation: () => { pathname: string; search: string; hash: string };
  navigate: (to: string) => Promise<void>; // resolves AFTER URL change
  resolveRoute?: (spec: RouteSpec) => ResolvedRoute; // override for params
  matches?: (resolved: ResolvedRoute, current: TourLocation) => boolean;
};
```

Step / section `route` accepts a string (`"/observe?range=24h"`) or a
`RouteSpec` (`{ path, params, search, hash, match }`).

## Events

The engine exposes a typed mitt bus. Use `tour.on(name, handler)` from the
engine, or `useTourEvent(name, handler)` from React. Names:

- `tour:start | tour:end`
- `section:enter | section:exit | section:skip`
- `section:introduction:show | section:introduction:acknowledge`
- `step:before-enter | step:enter | step:exit | step:advance`
- `target:found | target:lost`
- `navigation:before | navigation:after`

## Plugins

Plugins receive `{ bus, registerTrigger, registerHighlight, use }`. They may:

- Listen on `bus` for any tour lifecycle event (see Events above).
- Register new advance triggers via `registerTrigger("key", factory)` and
  reference them from `step.advanceOn` as `{ type: "custom", key: "key" }`.
- Register custom highlight shapes via `registerHighlight("shape", renderer)`
  (rendered by the default `Spotlight` once a plugin layer consumes the
  registry — `box`, `circle`, and `none` are built-in today).
- Push lifecycle middleware via `use(mw)` to run async side effects on every
  step enter.

Built-in plugins: [`createAnalyticsPlugin`](./plugins/createAnalyticsPlugin.ts).
Plugin `install` may return a cleanup; `engine.destroy()` runs it.
