# Tour (Phase 1)

A driver.js-like guided tour library. Phase 1 ships the headless engine, React
bindings, and a React Router 7 navigator adapter. The default MUI UI lands in
Phase 2.

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
└── index.ts                    # barrel
```

## Usage (Phase 1)

```tsx
import { createTour, TourProvider, TargetTracker, TourPortal, Spotlight, PopoverAnchor, useTour, useReactRouterNavigator } from "@/features/tour";

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
```

```tsx
function TourBridge({ children }: { children: React.ReactNode }) {
  const navigator = useReactRouterNavigator();
  return (
    <TourProvider tour={tour} navigator={navigator}>
      {children}
      <TourScene />
    </TourProvider>
  );
}

function TourScene() {
  const { actions, activeStep } = useTour();
  return (
    <TourPortal>
      <TargetTracker>
        {({ rect }) => (
          <>
            <Spotlight rect={rect} highlight={activeStep?.step.highlight} />
            <PopoverAnchor rect={rect} placement={activeStep?.step.placement ?? "bottom"}>
              {activeStep ? (
                <div style={{ background: "white", padding: 16, borderRadius: 8 }}>
                  <p>{typeof activeStep.step.content === "function" ? null : activeStep.step.content}</p>
                  <button onClick={() => actions.next()}>Next</button>
                </div>
              ) : null}
            </PopoverAnchor>
          </>
        )}
      </TargetTracker>
    </TourPortal>
  );
}
```

The default MUI-based scene (popover + intro dialog + skip controls) ships in
Phase 2, replacing the inline rendering above.

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

## Plugins (preview)

Plugins receive `{ bus, registerTrigger, registerHighlight, use }`. Phase 1
includes the plugin contract on the engine side; the analytics plugin and any
custom highlight renderers ship as part of the default UI in Phase 2.
