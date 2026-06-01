# Create Experiment Tour Instrumentation Design

## Goal

Instrument the prompt experiment creation flow in the task tour so users are guided through the full section-level Create Experiment modal flow, not just the entry point. The tour should use the existing composite-step pattern and the existing guided highlight popover companion.

The flow is successful only when an experiment is created. Opening the modal or partially completing it should not complete the tour objective.

## Current State

The Prompts tour section has a single `run-experiment` step that targets the Experiment button on the Prompt Runs tab. The menu item currently dispatches the experiment tour action before opening the modal, so the tour can advance before the user configures or creates anything.

The Create Experiment modal already has three logical sections:

- Experiment Info
- Configure Prompts
- Configure Evals

The tour engine already supports:

- Composite targets via query hooks
- `action-only` advancement
- Manual guided steps with `GuidedStepPopover`
- Target refresh through `refreshTaskTourTarget()`

## Proposed Flow

Replace the single `run-experiment` step with section-level tour steps:

1. `open-create-experiment`
   - Target: Experiment button or Create New menu path.
   - Behavior: guides the user to open the Create Experiment modal.
   - Completion: selecting Create New opens the modal and advances to the modal step.

2. `complete-experiment-info`
   - Target: Create Experiment modal, Experiment Info step body.
   - Popover: explains that the user should choose a name, prompt versions, dataset/version, optional row filters, and evaluators.
   - Completion: dispatches when the modal advances to Configure Prompts.

3. `complete-prompt-mapping`
   - Target: Create Experiment modal, Configure Prompts step body.
   - Popover: explains variable auto-mapping and required dataset-column mappings.
   - Completion: dispatches when the modal advances to Configure Evals, or when the user submits the no-evaluator path and starts creation from Configure Prompts.

4. `create-experiment`
   - Target: Create Experiment modal, Configure Evals step body when evaluators exist; otherwise the final Create Experiment button in Configure Prompts.
   - Popover: explains dataset column vs experiment output mappings when evals are present, and reinforces that Create Experiment is the durable completion event.
   - Completion: dispatches only from the create mutation `onSuccess`.

Optional controls, including dataset row filters and evaluator instruction links, remain available but are not separate tour steps.

## Engineering Changes

### Tour Selectors

Add new `TOUR_IDS` for:

- Create Experiment modal paper
- Experiment Info step body
- Configure Prompts step body
- Configure Evals step body
- Modal final Create Experiment button or action area

### Tour Actions

Add new `TASK_TOUR_ACTIONS` for:

- Create Experiment modal opened
- Experiment info completed
- Prompt mapping completed
- Experiment created

The existing `experimentRun` action should either be removed from this path or kept only as a backward-compatible alias if other code still relies on it.

### Tour Wiring

Update the Prompts section wiring:

- Replace `run-experiment` with the section-level steps above.
- Use `advance: "action-only"` for modal steps.
- Add `popover` config to modal steps so `GuidedStepPopover` displays the step copy near the highlighted modal area.
- Use query hooks for modal targets so the target resolver can prefer the currently visible modal step and fall back to the Experiment button before the modal opens.
- Resolve the final create step to the Configure Evals body when evaluators exist, and to the final Create Experiment button when the modal skips eval configuration.

### Product Instrumentation

Update the prompt experiment entry path:

- Clicking Create New should open the modal and dispatch the "modal opened" action.
- It should not dispatch final completion.

Update `CreateExperimentModal`:

- Add `data-tour-id` attributes to modal paper and section bodies.
- Call `refreshTaskTourTarget()` after the modal opens and after the form `section` changes.
- Dispatch section completion actions from modal submit transitions:
  - Info submit moves to Prompts and emits info completed.
  - Prompts submit moves to Evals and emits prompt mapping completed.
  - Prompts submit with no evaluators emits prompt mapping completed before starting creation; final success emits experiment created.
  - Evals submit creates the experiment; final success emits experiment created.
- Dispatch final completion only from create mutation success.

## Testing Plan

Add or update focused tests for:

- Tour config includes the new Prompts steps with `action-only` advancement and popover config.
- The old behavior no longer completes the experiment tour step just by choosing Create New.
- The Create Experiment modal exposes the expected `data-tour-id`s.
- Opening the modal and changing sections refreshes the active tour target.
- Section advancement dispatches the matching tour action.
- Successful experiment creation dispatches final completion.
- Failed experiment creation does not dispatch final completion.

## Non-Goals

- Do not add field-by-field tour steps.
- Do not create a second local mini-guide separate from the tour engine.
- Do not instrument optional dataset row filters or evaluator instruction links as mandatory steps.
- Do not redesign the Create Experiment modal UI beyond the tour-specific selectors and event hooks.
