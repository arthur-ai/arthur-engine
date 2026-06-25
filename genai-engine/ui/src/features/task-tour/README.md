# Task Tour Engineering Guide

This directory owns the Evals 101 tour runtime: engine config, target selectors,
step wiring, persistence widgets, and product-side event bridges. Marketing copy
lives in `content/*.md`; engineering wiring lives in `content/wiring.ts`.

## Composite Steps

Use a composite step when the user must start from one visible control, then
finish inside UI that appears later, such as a modal, popover, drawer, or panel.

Examples:

- Trace annotations: click the annotation trigger, review the annotations modal,
  then close the modal to complete the step.
- Manual feedback: click a feedback button, fill the feedback popover, then
  submit successfully to complete the step.
- Generate synthetic data: click the Generate button, configure the modal, then
  start generation or cancel the optional modal to complete the step.
- Evaluate results: open the Results tab, click the first result row, then
  close the details modal after reviewing it.
- Add trace to dataset: open Add to Dataset from a trace drawer, configure the
  drawer, then save the row successfully.

### Desired Behavior

A composite step has three separate concepts:

- **Initial target**: the trigger the user can see before the secondary UI opens.
- **Active surface target**: the modal/popover/drawer that should be highlighted
  after it opens.
- **Completion action**: the meaningful outcome that marks the step complete.

Do not complete a composite step just because the user opened a modal or popover.
Opening the surface only moves the spotlight. Completion should happen on the
real outcome: submit success, generation started, modal closed after review, and
so on. Optional steps may also complete on cancel when skipping the optional work
is an accepted outcome.

## Implementation Recipe

1. Add tour ids in `selectors.ts`.

   ```ts
   export const TOUR_IDS = {
     myTrigger: "task-tour-my-trigger",
     myModal: "task-tour-my-modal",
   } as const;
   ```

2. Add or reuse an action in `tourActions.ts`.

   ```ts
   export const TASK_TOUR_ACTIONS = {
     myStepCompleted: "task-tour:my-step-completed",
   } as const;
   ```

3. Add a query-hook id in `content/wiring.ts`.

   ```ts
   export const TASK_TOUR_QUERY_HOOKS = {
     myCompositeStep: "task-tour.myCompositeStep",
   } as const;
   ```

4. Wire the step as `action-only` and use the query hook as its target.

   ```ts
   "my-composite-step": {
     targetId: TOUR_IDS.myTrigger,
     targetHookId: TASK_TOUR_QUERY_HOOKS.myCompositeStep,
     actionName: TASK_TOUR_ACTIONS.myStepCompleted,
     advance: "action-only",
   },
   ```

   `action-only` matters: a click on the trigger should not complete the step.

5. Register a resolver widget that prefers the active surface and falls back to
   the trigger.

   ```tsx
   function makePreferredDataTourIdResolver(preferredId: TourId, fallbackId: TourId): () => Element | null {
     return () => document.querySelector(tourSelector(preferredId)) ?? document.querySelector(tourSelector(fallbackId));
   }

   export function MyTargetWidget() {
     const target = useMemo(() => makePreferredDataTourIdResolver(TOUR_IDS.myModal, TOUR_IDS.myTrigger), []);
     useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.myCompositeStep, target);
     return null;
   }
   ```

   Mount the widget under `TaskTourPortal` inside `TaskTour.tsx`.

6. Tag the trigger and the active surface.

   ```tsx
   <Button data-tour-id={TOUR_IDS.myTrigger}>Open modal</Button>

   <Dialog slotProps={{ paper: { "data-tour-id": TOUR_IDS.myModal } as HTMLAttributes<HTMLDivElement> }} />
   ```

7. Refresh the current target after the surface opens.

   ```tsx
   useEffect(() => {
     if (!open) return;
     const frame = window.requestAnimationFrame(() => refreshTaskTourTarget());
     return () => window.cancelAnimationFrame(frame);
   }, [open]);
   ```

   Use `requestAnimationFrame` so the resolver runs after React/MUI has mounted
   the surface.

8. Dispatch the completion action only on the meaningful outcome.

   ```ts
   const handleSubmitSuccess = () => {
     dispatchTourEvent(TASK_TOUR_EVENTS.myStepCompleted);
   };
   ```

## Testing Checklist

Add focused tests for each composite step:

- The tour config uses `targetHookId` and `advance: "action-only"`.
- Opening the modal/popover does not dispatch the completion action.
- The active surface receives its `data-tour-id`.
- The component calls `refreshTaskTourTarget()` after opening the surface.
- The completion action dispatches only on the intended outcome.

## Common Pitfalls

- **Completing on open**: opening a modal is not the outcome. Move the target,
  but do not dispatch the step action.
- **Forgetting the fallback target**: before the modal opens, the step still
  needs a visible trigger to highlight.
- **Refreshing too early**: call `refreshTaskTourTarget()` after mount, usually
  inside `requestAnimationFrame`.
- **Using click+action for composite steps**: default click advancement makes the
  trigger complete the step immediately. Use `advance: "action-only"`.
- **Importing the task-tour barrel from low-level components**: prefer scoped
  imports like `@/features/task-tour/selectors` and
  `@/features/task-tour/tourEvents` to avoid pulling unrelated app code into
  component tests.
