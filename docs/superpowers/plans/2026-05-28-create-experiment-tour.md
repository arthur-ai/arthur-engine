# Create Experiment Tour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guide users through the full prompt experiment creation modal flow with the existing task tour engine and guided highlight popover.

**Architecture:** Replace the single Prompts section `run-experiment` step with section-level action-only steps. Add query-hook target resolvers that retarget from the outer Experiment button to the active Create Experiment modal section. Product code emits tour actions only when the modal opens, section transitions occur, or experiment creation succeeds.

**Tech Stack:** React 19, TypeScript, MUI v7, Vitest, Testing Library, the existing `features/tour` engine, and the existing `features/task-tour` action/query-hook APIs.

---

## File Structure

- Modify `genai-engine/ui/src/features/task-tour/selectors.ts`
  - Add `TOUR_IDS` for Create Experiment modal targets.
- Modify `genai-engine/ui/src/features/task-tour/tourActions.ts`
  - Add typed actions for modal opened, info completed, prompt mapping completed, and experiment created.
- Modify `genai-engine/ui/src/features/task-tour/content/wiring.ts`
  - Add query hook IDs and replace `run-experiment` wiring with section-level modal steps.
- Modify `genai-engine/ui/src/features/task-tour/content/05-prompts.md`
  - Replace the single markdown step with four section-level step copy blocks.
- Modify `genai-engine/ui/src/features/task-tour/widgets/PromptTargetWidget.tsx`
  - Add resolvers for Create Experiment modal targets and register them.
- Modify `genai-engine/ui/src/features/task-tour/widgets/PromptTargetWidget.test.tsx`
  - Test resolver fallback/preference behavior.
- Modify `genai-engine/ui/src/features/task-tour/__tests__/tourConfig.test.ts`
  - Test new Prompts section wiring.
- Modify `genai-engine/ui/src/components/prompts/PromptsView.tsx`
  - Dispatch modal-open action from Create New instead of final completion.
- Create `genai-engine/ui/src/components/prompts/PromptsView.test.tsx`
  - Test Create New opens the modal path and does not dispatch final completion.
- Modify `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/index.tsx`
  - Add modal `data-tour-id`, target refreshes, and final success action.
- Modify `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/components/prompt-step/index.tsx`
  - Add final create target for the no-evaluator path.
- Modify `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/components/evals-step/index.tsx`
  - Add final create target for the evaluator path.
- Create `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/CreateExperimentModal.tour.test.tsx`
  - Test modal target ids, refresh, section actions, final success action, and failure behavior.

Do not commit during execution unless the user explicitly requests a commit.

---

### Task 1: Tour Config And Content

**Files:**
- Modify: `genai-engine/ui/src/features/task-tour/selectors.ts`
- Modify: `genai-engine/ui/src/features/task-tour/tourActions.ts`
- Modify: `genai-engine/ui/src/features/task-tour/content/wiring.ts`
- Modify: `genai-engine/ui/src/features/task-tour/content/05-prompts.md`
- Test: `genai-engine/ui/src/features/task-tour/__tests__/tourConfig.test.ts`

- [ ] **Step 1: Write the failing config test**

Add this test to `genai-engine/ui/src/features/task-tour/__tests__/tourConfig.test.ts` inside the existing `describe("task tour config", ...)` block:

```ts
  it("guides create experiment through modal sections with action-only popovers", () => {
    const config = buildTourConfig("task-id");
    const promptsSection = config.sections.find((section) => section.id === "prompts");

    const openCreateStep = promptsSection?.steps.find((step) => step.id === "open-create-experiment");
    const infoStep = promptsSection?.steps.find((step) => step.id === "complete-experiment-info");
    const promptMappingStep = promptsSection?.steps.find((step) => step.id === "complete-prompt-mapping");
    const createExperimentStep = promptsSection?.steps.find((step) => step.id === "create-experiment");

    expect(openCreateStep).toMatchObject({
      route: {
        path: "/tasks/:taskId/prompts",
        params: { taskId: "task-id" },
        search: { tab: "prompt-experiments" },
      },
      target: { kind: "selector", selector: tourSelector(TOUR_IDS.promptsExperimentButton) },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentModalOpened }],
    });

    expect(infoStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfo },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentInfoCompleted }],
      popover: { placement: "left" },
    });

    expect(promptMappingStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentPromptMappingsCompleted }],
      popover: { placement: "left" },
    });

    expect(createExperimentStep).toMatchObject({
      target: { kind: "queryHook", hookId: TASK_TOUR_QUERY_HOOKS.createExperimentFinal },
      advanceOn: [{ type: "action", name: TASK_TOUR_ACTIONS.createExperimentCreated }],
      popover: { placement: "left" },
    });
  });
```

- [ ] **Step 2: Run the config test and verify it fails**

Run:

```bash
cd genai-engine/ui && yarn test:run src/features/task-tour/__tests__/tourConfig.test.ts
```

Expected: FAIL because `TOUR_IDS.createExperimentInfo`, `TASK_TOUR_ACTIONS.createExperimentModalOpened`, and the new step IDs/query hooks do not exist yet.

- [ ] **Step 3: Add tour selectors**

Update `TOUR_IDS` in `genai-engine/ui/src/features/task-tour/selectors.ts` by adding these entries after `promptsExperimentButton`:

```ts
  /** Create Experiment dialog surface after the Prompt Runs Experiment menu opens it. */
  createExperimentModal: "task-tour-create-experiment-modal",
  /** Experiment Info section inside the Create Experiment dialog. */
  createExperimentInfoStep: "task-tour-create-experiment-info",
  /** Configure Prompts section inside the Create Experiment dialog. */
  createExperimentPromptMappingsStep: "task-tour-create-experiment-prompt-mappings",
  /** Configure Evals section inside the Create Experiment dialog. */
  createExperimentEvalMappingsStep: "task-tour-create-experiment-eval-mappings",
  /** Final Create Experiment action in the dialog. */
  createExperimentSubmit: "task-tour-create-experiment-submit",
```

- [ ] **Step 4: Add tour actions**

Update `TASK_TOUR_ACTIONS` in `genai-engine/ui/src/features/task-tour/tourActions.ts` by replacing or superseding the old `experimentRun` entry with these entries:

```ts
  createExperimentModalOpened: "task-tour:create-experiment-modal-opened",
  createExperimentInfoCompleted: "task-tour:create-experiment-info-completed",
  createExperimentPromptMappingsCompleted: "task-tour:create-experiment-prompt-mappings-completed",
  createExperimentCreated: "task-tour:create-experiment-created",
```

Keep this alias only if any tests or product code still reference `experimentRun` after the implementation:

```ts
  experimentRun: "task-tour:create-experiment-modal-opened",
```

- [ ] **Step 5: Add query hook IDs and wiring**

Update `TASK_TOUR_QUERY_HOOKS` in `genai-engine/ui/src/features/task-tour/content/wiring.ts`:

```ts
  createExperimentInfo: "task-tour.createExperimentInfo",
  createExperimentPromptMappings: "task-tour.createExperimentPromptMappings",
  createExperimentFinal: "task-tour.createExperimentFinal",
```

Then replace the existing `run-experiment` step in the Prompts section with:

```ts
      "open-create-experiment": {
        targetId: TOUR_IDS.promptsExperimentButton,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentModalOpened,
        advance: "action-only",
      },
      "complete-experiment-info": {
        targetId: TOUR_IDS.createExperimentInfoStep,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentInfo,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentInfoCompleted,
        advance: "action-only",
        popover: { placement: "left" },
      },
      "complete-prompt-mapping": {
        targetId: TOUR_IDS.createExperimentPromptMappingsStep,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentPromptMappingsCompleted,
        advance: "action-only",
        popover: { placement: "left" },
      },
      "create-experiment": {
        targetId: TOUR_IDS.createExperimentEvalMappingsStep,
        targetHookId: TASK_TOUR_QUERY_HOOKS.createExperimentFinal,
        route: "prompts",
        search: { tab: "prompt-experiments" },
        actionName: TASK_TOUR_ACTIONS.createExperimentCreated,
        advance: "action-only",
        popover: { placement: "left" },
      },
```

- [ ] **Step 6: Update prompts tour content**

In `genai-engine/ui/src/features/task-tour/content/05-prompts.md`, replace the old `run-experiment` step entry in frontmatter with:

```md
  - id: open-create-experiment
    title: Start an experiment
  - id: complete-experiment-info
    title: Configure experiment info
  - id: complete-prompt-mapping
    title: Map prompt variables
  - id: create-experiment
    title: Create the experiment
```

Then replace the old `## step: run-experiment` body with:

```md
## step: open-create-experiment

Open the Experiment menu and choose **Create New**. The tour will stay with you inside the modal while you configure the run.

## step: complete-experiment-info

Fill out the experiment basics: name the run, choose the candidate prompt versions, select the dataset version with the captured failure, and add the evals that should judge the result.

## step: complete-prompt-mapping

Map each prompt variable to the dataset column that should feed it. Exact name matches are filled in for you, but review them before continuing.

## step: create-experiment

Review the final mappings, then click **Create Experiment**. If evals are configured, choose whether each eval variable comes from the dataset or from the prompt output before creating the run.
```

- [ ] **Step 7: Run the config test and verify it passes**

Run:

```bash
cd genai-engine/ui && yarn test:run src/features/task-tour/__tests__/tourConfig.test.ts
```

Expected: PASS.

---

### Task 2: Query Hook Resolvers

**Files:**
- Modify: `genai-engine/ui/src/features/task-tour/widgets/PromptTargetWidget.tsx`
- Test: `genai-engine/ui/src/features/task-tour/widgets/PromptTargetWidget.test.tsx`

- [ ] **Step 1: Write failing resolver tests**

Add these tests to `PromptTargetWidget.test.tsx`:

```ts
  it("targets Create Experiment info step after the modal opens", () => {
    document.body.innerHTML = `<button data-tour-id="${TOUR_IDS.promptsExperimentButton}">Experiment</button>`;
    const trigger = document.querySelector("button");

    expect(resolveCreateExperimentInfoTarget()).toBe(trigger);

    document.body.innerHTML += `<section data-tour-id="${TOUR_IDS.createExperimentInfoStep}">Experiment Info</section>`;
    expect(resolveCreateExperimentInfoTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.createExperimentInfoStep}"]`));
  });

  it("targets Create Experiment prompt mappings after that modal section is visible", () => {
    document.body.innerHTML = `
      <section data-tour-id="${TOUR_IDS.createExperimentModal}">Create Experiment</section>
      <section data-tour-id="${TOUR_IDS.createExperimentPromptMappingsStep}">Prompt mappings</section>
    `;

    expect(resolveCreateExperimentPromptMappingsTarget()).toBe(
      document.querySelector(`[data-tour-id="${TOUR_IDS.createExperimentPromptMappingsStep}"]`)
    );
  });

  it("targets eval mappings for final create when present, otherwise the create button", () => {
    document.body.innerHTML = `
      <button data-tour-id="${TOUR_IDS.createExperimentSubmit}">Create Experiment</button>
    `;
    const createButton = document.querySelector("button");

    expect(resolveCreateExperimentFinalTarget()).toBe(createButton);

    document.body.innerHTML += `<section data-tour-id="${TOUR_IDS.createExperimentEvalMappingsStep}">Eval mappings</section>`;
    expect(resolveCreateExperimentFinalTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.createExperimentEvalMappingsStep}"]`));
  });
```

Update the import at the top of the test file:

```ts
import {
  resolveCreateExperimentFinalTarget,
  resolveCreateExperimentInfoTarget,
  resolveCreateExperimentPromptMappingsTarget,
  resolvePlaygroundPromptCardTarget,
  resolvePromptOpenInPlaygroundTarget,
  resolvePromptTagsTarget,
} from "./PromptTargetWidget";
```

- [ ] **Step 2: Run the resolver test and verify it fails**

Run:

```bash
cd genai-engine/ui && yarn test:run src/features/task-tour/widgets/PromptTargetWidget.test.tsx
```

Expected: FAIL because the new resolver exports do not exist.

- [ ] **Step 3: Implement resolvers and registrations**

Add these exports to `genai-engine/ui/src/features/task-tour/widgets/PromptTargetWidget.tsx`:

```ts
export function resolveCreateExperimentInfoTarget(): Element | null {
  return document.querySelector(tourSelector(TOUR_IDS.createExperimentInfoStep)) ?? document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton));
}

export function resolveCreateExperimentPromptMappingsTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentPromptMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal)) ??
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
  );
}

export function resolveCreateExperimentFinalTarget(): Element | null {
  return (
    document.querySelector(tourSelector(TOUR_IDS.createExperimentEvalMappingsStep)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentSubmit)) ??
    document.querySelector(tourSelector(TOUR_IDS.createExperimentModal)) ??
    document.querySelector(tourSelector(TOUR_IDS.promptsExperimentButton))
  );
}
```

Register them in `PromptTargetWidget`:

```tsx
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentInfo, resolveCreateExperimentInfoTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentPromptMappings, resolveCreateExperimentPromptMappingsTarget);
  useRegisterQueryHook(TASK_TOUR_QUERY_HOOKS.createExperimentFinal, resolveCreateExperimentFinalTarget);
```

- [ ] **Step 4: Run resolver test and verify it passes**

Run:

```bash
cd genai-engine/ui && yarn test:run src/features/task-tour/widgets/PromptTargetWidget.test.tsx
```

Expected: PASS.

---

### Task 3: Prompt Experiments Entry Action

**Files:**
- Modify: `genai-engine/ui/src/components/prompts/PromptsView.tsx`
- Create: `genai-engine/ui/src/components/prompts/PromptsView.test.tsx`

- [ ] **Step 1: Write failing entry test**

Create `genai-engine/ui/src/components/prompts/PromptsView.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PromptsView } from "./PromptsView";

import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";

const setActiveTab = vi.fn();

vi.mock("nuqs", () => ({
  parseAsStringEnum: () => ({
    withDefault: () => ({}),
  }),
  useQueryState: () => ["prompt-experiments", setActiveTab],
}));

vi.mock("../notebooks/Notebooks", () => ({
  default: () => <div>Notebooks</div>,
}));

vi.mock("../prompts-management/PromptsManagement", () => ({
  default: () => <div>Prompts management</div>,
}));

vi.mock("../prompt-experiments/PromptExperimentsView", () => ({
  PromptExperimentsView: ({ onRegisterCreate }: { onRegisterCreate?: (fn: () => void) => void }) => {
    onRegisterCreate?.(vi.fn());
    return <div>Prompt experiments</div>;
  },
}));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  TASK_TOUR_EVENTS: {
    createExperimentModalOpened: "task-tour:create-experiment-modal-opened",
    createExperimentCreated: "task-tour:create-experiment-created",
  },
}));

describe("PromptsView create experiment tour action", () => {
  it("dispatches modal opened, not final completion, when Create New is selected", () => {
    render(<PromptsView />);

    fireEvent.click(screen.getByRole("button", { name: /experiment/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /create new/i }));

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentModalOpened);
    expect(dispatchTourEvent).not.toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);
  });
});
```

- [ ] **Step 2: Run the entry test and verify it fails**

Run:

```bash
cd genai-engine/ui && yarn test:run src/components/prompts/PromptsView.test.tsx
```

Expected: FAIL while `PromptsView` still dispatches the old experiment action or lacks `createExperimentModalOpened`.

- [ ] **Step 3: Update Create New action dispatch**

In `genai-engine/ui/src/components/prompts/PromptsView.tsx`, update the Create New `MenuItem` handler:

```tsx
                onClick={() => {
                  setExperimentsMenuAnchor(null);
                  dispatchTourEvent(TASK_TOUR_EVENTS.createExperimentModalOpened);
                  experimentsCreateFn.current();
                }}
```

Ensure no final completion action is dispatched from this menu handler.

- [ ] **Step 4: Run the entry test and verify it passes**

Run:

```bash
cd genai-engine/ui && yarn test:run src/components/prompts/PromptsView.test.tsx
```

Expected: PASS.

---

### Task 4: Create Experiment Modal Instrumentation

**Files:**
- Modify: `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/index.tsx`
- Modify: `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/components/prompt-step/index.tsx`
- Modify: `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/components/evals-step/index.tsx`
- Create: `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/CreateExperimentModal.tour.test.tsx`

- [ ] **Step 1: Write failing modal tour test**

Create `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/CreateExperimentModal.tour.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CreateExperimentModal } from ".";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourActions";

const mutationState = vi.hoisted(() => ({
  options: null as null | { onSuccess?: (data: { id: string; name: string }) => void; onError?: (error: Error) => void },
  mutateAsync: vi.fn(),
}));

const formState = vi.hoisted(() => ({
  values: {
    section: "info" as "info" | "prompts" | "evals",
    info: {
      evaluators: [{ name: "readability", version: 1 }],
    },
  },
  isDirty: false,
  isSubmitting: false,
}));

const formApi = vi.hoisted(() => ({
  handleSubmit: vi.fn(),
  reset: vi.fn(),
  setFieldValue: vi.fn((name: string, value: "info" | "prompts" | "evals") => {
    if (name === "section") formState.values.section = value;
  }),
}));

vi.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: vi.fn() }),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("@tanstack/react-form", () => ({
  useStore: (_store: unknown, selector: (state: typeof formState) => unknown) => selector(formState),
}));

vi.mock("@/components/traces/components/filtering/hooks/form", () => ({
  useAppForm: (options: { onSubmit: (args: { value: typeof formState.values; formApi: typeof formApi }) => Promise<void> }) => ({
    ...formApi,
    store: {},
    state: formState,
    handleSubmit: () => options.onSubmit({ value: formState.values, formApi }),
  }),
}));

vi.mock("@/hooks/useTask", () => ({
  useTask: () => ({ task: { id: "task-id" } }),
}));

vi.mock("@/hooks/usePromptExperiments", () => ({
  usePromptExperiment: () => ({ experiment: undefined, isLoading: false }),
  useCreateExperiment: (taskId: string, options: typeof mutationState.options) => {
    mutationState.options = options;
    return mutationState;
  },
}));

vi.mock("./components/info-step", () => ({
  InfoStep: ({ onCancel }: { onCancel: () => void }) => (
    <div data-testid="info-step">
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

vi.mock("./components/prompt-step", () => ({
  PromptStep: () => <div data-testid="prompt-step">Prompt step</div>,
}));

vi.mock("./components/evals-step", () => ({
  EvalsStep: () => <div data-testid="evals-step">Evals step</div>,
}));

vi.mock("@/components/common/ConfirmationModal", () => ({
  ConfirmationModal: ({ open }: { open: boolean; children?: ReactNode }) => (open ? <div>Discard changes?</div> : null),
}));

vi.mock("@/features/task-tour/tourActions", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    createExperimentInfoCompleted: "task-tour:create-experiment-info-completed",
    createExperimentPromptMappingsCompleted: "task-tour:create-experiment-prompt-mappings-completed",
    createExperimentCreated: "task-tour:create-experiment-created",
  },
}));

describe("CreateExperimentModal task tour instrumentation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mutationState.options = null;
    mutationState.mutateAsync.mockReset();
    formState.values.section = "info";
    formState.values.info.evaluators = [{ name: "readability", version: 1 }];
  });

  it("marks the dialog and refreshes the tour target when opened", async () => {
    render(<CreateExperimentModal open onClose={vi.fn()} />);

    expect(screen.getByRole("dialog").getAttribute("data-tour-id")).toBe(TOUR_IDS.createExperimentModal);
    expect(screen.getByTestId("info-step").parentElement?.getAttribute("data-tour-id")).toBe(TOUR_IDS.createExperimentInfoStep);
    await waitFor(() => expect(refreshTaskTourTarget).toHaveBeenCalled());
    expect(dispatchTourEvent).not.toHaveBeenCalled();
  });

  it("dispatches final creation only from mutation success", () => {
    render(<CreateExperimentModal open onClose={vi.fn()} />);

    expect(dispatchTourEvent).not.toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);

    mutationState.options?.onSuccess?.({ id: "experiment-id", name: "Experiment" });

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);
  });

  it("dispatches info completion only when the form advances from info to prompts", () => {
    const { container } = render(<CreateExperimentModal open onClose={vi.fn()} />);

    fireEvent.submit(container.querySelector("form")!);

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentInfoCompleted);
    expect(formApi.setFieldValue).toHaveBeenCalledWith("section", "prompts");
  });

  it("dispatches prompt mapping completion when the form advances from prompts to evals", () => {
    formState.values.section = "prompts";
    const { container } = render(<CreateExperimentModal open onClose={vi.fn()} />);

    fireEvent.submit(container.querySelector("form")!);

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentPromptMappingsCompleted);
    expect(formApi.setFieldValue).toHaveBeenCalledWith("section", "evals");
  });

  it("does not dispatch final creation when mutation errors", () => {
    render(<CreateExperimentModal open onClose={vi.fn()} />);

    mutationState.options?.onError?.(new Error("failed"));

    expect(dispatchTourEvent).not.toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);
  });
});
```

- [ ] **Step 2: Run the modal test and verify it fails**

Run:

```bash
cd genai-engine/ui && yarn test:run src/components/prompt-experiments/create-experiment-modal/CreateExperimentModal.tour.test.tsx
```

Expected: FAIL because modal tour IDs and final success dispatch do not exist yet.

- [ ] **Step 3: Add modal paper target, refresh, and final success action**

In `genai-engine/ui/src/components/prompt-experiments/create-experiment-modal/index.tsx`, add imports:

```ts
import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourActions";
```

Add `useEffect` to the React import:

```ts
import { useCallback, useEffect, useState } from "react";
```

Update the outer `Dialog`:

```tsx
    <Dialog
      open={open}
      maxWidth="md"
      fullWidth
      aria-labelledby="create-experiment-dialog-title"
      slotProps={{ paper: { "data-tour-id": TOUR_IDS.createExperimentModal } as React.HTMLAttributes<HTMLDivElement> }}
    >
```

Add target refreshes inside `CreateExperimentModalInner` after `section` is defined:

```ts
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => refreshTaskTourTarget());
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => refreshTaskTourTarget());
    return () => window.cancelAnimationFrame(frame);
  }, [section]);
```

Update `useCreateExperiment` `onSuccess`:

```ts
    onSuccess: (data) => {
      dispatchTourEvent(TASK_TOUR_EVENTS.createExperimentCreated);
      enqueueSnackbar(`Experiment "${data.name}" created successfully!`, { variant: "success" });
      navigate(`/tasks/${task!.id}/prompt-experiments/${data.id}`);
      onClose();
    },
```

- [ ] **Step 4: Add section wrapper targets**

In `index.tsx`, wrap each section component:

```tsx
        {section === "info" && (
          <Box data-tour-id={TOUR_IDS.createExperimentInfoStep}>
            <InfoStep form={form} onCancel={handleCancel} />
          </Box>
        )}
        {section === "prompts" && (
          <Box data-tour-id={TOUR_IDS.createExperimentPromptMappingsStep}>
            <PromptStep form={form} onCancel={handleCancel} />
          </Box>
        )}
        {section === "evals" && (
          <Box data-tour-id={TOUR_IDS.createExperimentEvalMappingsStep}>
            <EvalsStep form={form} onCancel={handleCancel} />
          </Box>
        )}
```

- [ ] **Step 5: Dispatch section completion actions after valid form transitions**

In `index.tsx`, dispatch info completion in the form `onSubmit` branch for `value.section === "info"` immediately before the section changes:

```ts
      if (value.section === "info") {
        dispatchTourEvent(TASK_TOUR_EVENTS.createExperimentInfoCompleted);
        return formApi.setFieldValue("section", "prompts");
      }
```

Then dispatch prompt mapping completion in the form `onSubmit` branch for `value.section === "prompts"`:

```ts
      if (value.section === "prompts") {
        dispatchTourEvent(TASK_TOUR_EVENTS.createExperimentPromptMappingsCompleted);
        if (value.info.evaluators.length === 0) {
          const request = { ...formDataToRequest(value), eval_list: [] };
          await createExperiment.mutateAsync(request);
          formApi.reset();
          return;
        }
        return formApi.setFieldValue("section", "evals");
      }
```

- [ ] **Step 6: Mark final create button in prompt step**

In `components/prompt-step/index.tsx`, add:

```ts
import { TOUR_IDS } from "@/features/task-tour/selectors";
```

Add the final target id to the no-evaluator create button:

```tsx
              <Button type="submit" variant="contained" loading={!hasEvaluators && isSubmitting} data-tour-id={!hasEvaluators ? TOUR_IDS.createExperimentSubmit : undefined}>
                {hasEvaluators ? "Configure Evals" : "Create Experiment"}
              </Button>
```

If TypeScript rejects `undefined` for `data-tour-id`, use a conditional spread:

```tsx
              <Button
                type="submit"
                variant="contained"
                loading={!hasEvaluators && isSubmitting}
                {...(!hasEvaluators ? { "data-tour-id": TOUR_IDS.createExperimentSubmit } : {})}
              >
```

- [ ] **Step 7: Mark final create button in evals step**

In `components/evals-step/index.tsx`, add:

```ts
import { TOUR_IDS } from "@/features/task-tour/selectors";
```

Update the final button:

```tsx
              <Button type="submit" variant="contained" loading={isSubmitting} data-tour-id={TOUR_IDS.createExperimentSubmit}>
                Create Experiment
              </Button>
```

- [ ] **Step 8: Run modal tour test and verify it passes**

Run:

```bash
cd genai-engine/ui && yarn test:run src/components/prompt-experiments/create-experiment-modal/CreateExperimentModal.tour.test.tsx
```

Expected: PASS. If the mocks need small adjustments for TanStack Form wrappers, keep the assertions focused on tour IDs, target refresh, and final success dispatch.

---

### Task 5: Verification

**Files:**
- Verify all files changed by Tasks 1-4.

- [ ] **Step 1: Run focused tour and modal tests**

Run:

```bash
cd genai-engine/ui && yarn test:run src/features/task-tour/__tests__/tourConfig.test.ts src/features/task-tour/widgets/PromptTargetWidget.test.tsx src/components/prompts/PromptsView.test.tsx src/components/prompt-experiments/create-experiment-modal/CreateExperimentModal.tour.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run TypeScript check**

Run:

```bash
cd genai-engine/ui && yarn type-check
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```bash
cd genai-engine/ui && yarn lint
```

Expected: PASS.

- [ ] **Step 4: Run format check**

Run:

```bash
cd genai-engine/ui && yarn format:check
```

Expected: PASS. If it fails only because edited files need formatting, run `cd genai-engine/ui && yarn format`, then rerun `yarn format:check`.

- [ ] **Step 5: Run full UI check**

Run:

```bash
cd genai-engine/ui && yarn check
```

Expected: PASS.

---

## Self-Review Notes

- Spec coverage: the plan covers composite target wiring, guided popovers, modal section-level targets, action-only advancement, target refresh, success-only final completion, and focused tests.
- Placeholder scan: no placeholder steps remain; each task has exact files, code snippets, commands, and expected outcomes.
- Type consistency: new selectors use `TOUR_IDS.createExperiment*`, actions use `TASK_TOUR_ACTIONS/TASK_TOUR_EVENTS.createExperiment*`, and query hooks use `TASK_TOUR_QUERY_HOOKS.createExperiment*` consistently.
