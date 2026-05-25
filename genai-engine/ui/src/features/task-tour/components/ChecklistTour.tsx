import { useCallback, useMemo, type ReactNode } from "react";

import { TASK_TOUR_SECTIONS, type TaskTourItem } from "../data";
import { isStubStep } from "../tour-config";
import { TASK_TOUR_TARGET_LOST_HINTS } from "../tourEventNames";

import { ChecklistPanel } from "./ChecklistPanel";
import { SectionIntroDialog } from "./SectionIntroDialog";

import {
  applyBackdropAction,
  BackdropBlocker,
  getHighlightPadding,
  Spotlight,
  TargetTracker,
  TourPortal,
  useActiveTarget,
  useChecklistProgress,
  useTour,
  useTourEngine,
  useTourEvent,
  type ChecklistProgressPlugin,
  type StepEnterEvent,
  type StepRenderContext,
} from "@/features/tour";

// MUI's default modal z-index is 1300 — keep the spotlight + ring above it so
// while a dialog is closed the highlight still appears on top of any non-modal
// MUI surface (tooltips at 1500 are the highest we expect).
//
// Layering rationale (low → high):
//   spotlight  (visual dim, pointer-events: none)  → 1399
//   pulse ring (decorative, pointer-events: none)  → 1400 (painted by the
//                                                    `task-tour-pulse`
//                                                    custom highlight, one
//                                                    tier above the
//                                                    spotlight base)
//   blocker    (pointer trap around the cutout)    → 1401
//   panel      (interactive checklist)             → 1450 (lives in ChecklistPanel)
// The blocker sits above the visual spotlight and below the panel so the
// panel stays clickable while the rest of the page is frozen.
const SPOTLIGHT_Z_INDEX = 1399;
const BLOCKER_Z_INDEX = 1401;

const TOTAL_ITEM_COUNT = TASK_TOUR_SECTIONS.reduce((sum, s) => sum + Math.max(1, s.items.length), 0);

function itemKey(sectionId: string, itemId: string) {
  return `${sectionId}.${itemId}`;
}

export interface ChecklistTourProps {
  /** When false, the entire walkthrough overlay (modal, panel, spotlight) is hidden. */
  enabled: boolean;
  /**
   * Persistence-backed item-progress plugin. Owned by the parent so progress
   * survives engine recreation (StrictMode dev re-mount, taskId changes) and
   * page reloads. Reads happen via {@link useChecklistProgress}; writes go
   * through `progressPlugin.add` / `toggle`.
   */
  progressPlugin: ChecklistProgressPlugin;
  /** Called when the tour reaches its end (last section completed). */
  onComplete: () => void;
  /** When set, positions the checklist panel next to this anchor rect. */
  panelAnchorRect?: DOMRect | null;
}

/**
 * The orchestrating layer: subscribes to engine state, drives the section
 * intro modal, paints the spotlight + pulsing ring on the current target, and
 * mirrors per-step progress into the `progressPlugin` so the floating
 * checklist can tick items off as the user works through the tour. Per-step
 * progress is recorded by the plugin automatically via `step:advance` for
 * both real and stub steps — `actions.next()` now emits `step:advance` for
 * the step it's leaving, so stubs no longer need a manual `progressPlugin.add`.
 *
 * Stub sections (intro-only) are handled by `acknowledgeIntroduction()` →
 * engine enters a placeholder step → we wait for `step:enter` and then call
 * `actions.next()` so the engine advances to the next section's intro
 * handshake. The intro progress key is then recorded by the plugin from the
 * resulting `step:advance` emission.
 */
export function ChecklistTour({ enabled, progressPlugin, onComplete, panelAnchorRect }: ChecklistTourProps) {
  const engine = useTourEngine();
  const { state, activeStep, actions } = useTour();
  const completedItemKeys = useChecklistProgress(progressPlugin);
  const activeTarget = useActiveTarget();

  const currentSectionIndex = state.status === "running" ? state.sectionIndex : 0;
  const currentStepIndex = state.status === "running" && !state.introductionPending ? state.stepIndex : -1;
  const currentSection = TASK_TOUR_SECTIONS[currentSectionIndex];

  // Stash an active target rect, ignored for stub steps so the body element
  // doesn't get spotlighted.
  const isOnStub = activeStep ? isStubStep(activeStep.step.id) : false;

  const introOpen = state.status === "running" && state.introductionPending;

  // Stubs have no UI of their own — once the engine enters one (after the
  // intro modal is acknowledged or on resume) we synthesise an immediate
  // advance so the user is never stranded on a placeholder.
  useTourEvent(
    "step:enter",
    useCallback(
      (event: StepEnterEvent) => {
        if (!isStubStep(event.stepId)) return;
        actions.next();
      },
      [actions]
    )
  );

  useTourEvent(
    "tour:end",
    useCallback(
      (event) => {
        if (event.reason === "completed") onComplete();
      },
      [onComplete]
    )
  );

  const handleStart = useCallback(() => {
    actions.acknowledgeIntroduction();
  }, [actions]);

  const handleDismiss = useCallback(() => {
    // `dismiss()` pauses the engine (preserving step position for the
    // FAB-driven resume) and emits `tour:dismiss` so the persistence plugin
    // marks the tour as `"dismissed"`. The parent then re-renders into the
    // resume-FAB branch via the persistence subscription.
    actions.dismiss();
  }, [actions]);

  const handleSelectItem = useCallback(
    (item: TaskTourItem, itemIndex: number) => {
      if (state.status !== "running") return;
      if (state.sectionId === currentSection?.id && itemIndex === currentStepIndex) return;
      actions.goTo({ sectionId: currentSection!.id, stepId: item.id });
    },
    [actions, currentSection, currentStepIndex, state]
  );

  const handleToggleItem = useCallback(
    (item: TaskTourItem) => {
      if (!currentSection) return;
      const key = itemKey(currentSection.id, item.id);
      // `toggle` returns the new state; if the user just *checked* the
      // engine's current step, advance via `actions.next()` so the engine
      // exits the step, emits `step:advance` (which the progress plugin
      // records — idempotent against the manual `toggle` above), and
      // handles section transitions cleanly.
      const nowComplete = progressPlugin.toggle(key);
      if (nowComplete && state.status === "running" && state.sectionId === currentSection.id && state.stepId === item.id) {
        actions.next();
      }
    },
    [actions, currentSection, progressPlugin, state]
  );

  const handleSelectSection = useCallback(
    (sectionIndex: number) => {
      const target = TASK_TOUR_SECTIONS[sectionIndex];
      if (!target) return;
      actions.goTo({ sectionId: target.id });
    },
    [actions]
  );

  const handlePrevSection = useCallback(() => {
    const prev = TASK_TOUR_SECTIONS[currentSectionIndex - 1];
    if (prev) actions.goTo({ sectionId: prev.id });
  }, [actions, currentSectionIndex]);

  const handleNextSection = useCallback(() => {
    const next = TASK_TOUR_SECTIONS[currentSectionIndex + 1];
    if (next) actions.goTo({ sectionId: next.id });
  }, [actions, currentSectionIndex]);

  const totalProgress = useMemo(() => {
    if (TOTAL_ITEM_COUNT === 0) return 0;
    return completedItemKeys.size / TOTAL_ITEM_COUNT;
  }, [completedItemKeys]);

  // Resolve `step.content` into a `ReactNode` so the checklist row reads from
  // the engine's `StepConfig` rather than `TaskTourItem.instructions`. Mirrors
  // `DefaultStepPopover`'s pattern so author-supplied function content is
  // supported alongside plain strings / nodes.
  const activeStepContent = useMemo<ReactNode | null>(() => {
    if (!activeStep) return null;
    if (isStubStep(activeStep.step.id)) return null;
    const { step, section, sectionIndex, stepIndex, globalStepIndex, totalSteps } = activeStep;
    if (typeof step.content !== "function") return step.content;
    const ctx: StepRenderContext = {
      tourId: engine.config.id,
      sectionId: section.id,
      stepId: step.id,
      index: { sectionIndex, stepIndex, globalStepIndex, totalSteps },
      actions,
    };
    return step.content(ctx);
  }, [activeStep, actions, engine.config.id]);

  const activeStepKey =
    state.status === "running" && !state.introductionPending && currentSection && state.stepId && !isStubStep(state.stepId)
      ? `${state.sectionId}.${state.stepId}`
      : null;
  const targetLostHint =
    activeStepKey && !activeTarget && !isOnStub ? (TASK_TOUR_TARGET_LOST_HINTS[activeStepKey] ?? null) : null;

  if (!enabled) return null;
  if (state.status === "idle") return null;

  const showPanel = state.status === "running" && !state.introductionPending;
  const showSpotlight = state.status === "running" && !state.introductionPending && !isOnStub;

  return (
    <TourPortal>
      <SectionIntroDialog
        open={introOpen}
        section={currentSection ?? null}
        sectionIndex={currentSectionIndex}
        onStart={handleStart}
        onDismiss={handleDismiss}
      />

      {showSpotlight ? (
        <TargetTracker>
          {({ rect }) => {
            // When the target hasn't resolved (e.g. event-only placeholder
            // steps targeting elements that don't exist yet), suppress the
            // entire spotlight (and matching pointer-blocker) rather than
            // dropping a flat backdrop over the page — the panel still
            // surfaces the instruction and the page stays usable until the
            // target appears.
            if (!rect) return null;
            const overlay = activeStep?.step.overlay;
            const showBlocker = overlay?.blockInteraction === true;
            return (
              <>
                {/* The `task-tour-pulse` custom highlight (registered by
                    `createTaskTourHighlightsPlugin`) renders both the box
                    cutout and the brand-coloured pulse ring. `Spotlight`
                    delegates to it via `engine.getHighlight(key)` when the
                    step's `highlight.shape === "custom"`. */}
                <Spotlight
                  rect={rect}
                  highlight={activeStep?.step.highlight}
                  // Source of truth is `step.overlay.color` from the engine
                  // config (set by `buildStep`); the literal here is a
                  // defensive default for any step that omits the field.
                  backdropColor={overlay?.color ?? "rgba(15, 23, 42, 0.28)"}
                  style={{ zIndex: SPOTLIGHT_Z_INDEX }}
                />
                {showBlocker ? (
                  <BackdropBlocker
                    cutoutRect={rect}
                    padding={getHighlightPadding(activeStep?.step.highlight)}
                    onBackdropClick={() => applyBackdropAction(overlay?.onBackdropClick, actions)}
                    style={{ zIndex: BLOCKER_Z_INDEX }}
                  />
                ) : null}
              </>
            );
          }}
        </TargetTracker>
      ) : null}

      {showPanel && currentSection ? (
        <ChecklistPanel
          currentSectionIndex={currentSectionIndex}
          currentItemIndex={currentStepIndex}
          activeStepContent={activeStepContent}
          targetLostHint={targetLostHint}
          completedItemKeys={completedItemKeys}
          totalItemCount={TOTAL_ITEM_COUNT}
          totalProgress={totalProgress}
          onSelectItem={handleSelectItem}
          onToggleItem={handleToggleItem}
          onSelectSection={handleSelectSection}
          onPrevSection={handlePrevSection}
          onNextSection={handleNextSection}
          onClose={handleDismiss}
          anchorRect={panelAnchorRect}
        />
      ) : null}
    </TourPortal>
  );
}
