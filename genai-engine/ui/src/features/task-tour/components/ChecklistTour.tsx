import { useCallback, useMemo, type ReactNode } from "react";

import { TASK_TOUR_SECTIONS, type TaskTourItem } from "../data";
import { isStubStep } from "../tour-config";
import { dispatchTourEvent } from "../tourEvents";

import { ChecklistPanel } from "./ChecklistPanel";
import { PulsingRing } from "./PulsingRing";
import { SectionIntroDialog } from "./SectionIntroDialog";

import {
  applyBackdropAction,
  BackdropBlocker,
  getHighlightPadding,
  Spotlight,
  TargetTracker,
  TourPortal,
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
//   blocker    (pointer trap around the cutout)     → 1401
//   pulse ring (decorative, pointer-events: none)   → 1400
//   panel      (interactive checklist)              → 1450 (lives in ChecklistPanel)
// The blocker sits above the visual spotlight and below the panel so the
// panel stays clickable while the rest of the page is frozen.
const SPOTLIGHT_Z_INDEX = 1399;
const PULSE_RING_Z_INDEX = 1400;
const BLOCKER_Z_INDEX = 1401;

const TOTAL_ITEM_COUNT = TASK_TOUR_SECTIONS.reduce((sum, s) => sum + Math.max(1, s.items.length), 0);

function itemKey(sectionId: string, itemId: string) {
  return `${sectionId}.${itemId}`;
}
function introKey(sectionId: string) {
  return `${sectionId}.__intro`;
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
}

/**
 * The orchestrating layer: subscribes to engine state, drives the section
 * intro modal, paints the spotlight + pulsing ring on the current target, and
 * mirrors per-step progress into the `progressPlugin` so the floating
 * checklist can tick items off as the user works through the tour. Real-step
 * advances are recorded by the plugin automatically via `step:advance`; stub
 * sections are recorded manually because `actions.next()` skips that bus
 * event by design.
 *
 * Stub sections (intro-only) are handled by `acknowledgeIntroduction()` →
 * engine enters a placeholder step → we wait for `step:enter` and then call
 * `actions.next()` so the engine advances to the next section's intro
 * handshake.
 */
export function ChecklistTour({ enabled, progressPlugin, onComplete }: ChecklistTourProps) {
  const engine = useTourEngine();
  const { state, activeStep, actions } = useTour();
  const completedItemKeys = useChecklistProgress(progressPlugin);

  const currentSectionIndex = state.status === "running" ? state.sectionIndex : 0;
  const currentStepIndex = state.status === "running" && !state.introductionPending ? state.stepIndex : -1;
  const currentSection = TASK_TOUR_SECTIONS[currentSectionIndex];

  // Stash an active target rect, ignored for stub steps so the body element
  // doesn't get spotlighted.
  const isOnStub = activeStep ? isStubStep(activeStep.step.id) : false;

  const introOpen = state.status === "running" && state.introductionPending;

  // Stubs have no UI of their own — once the engine enters one (after the
  // intro modal is acknowledged or on resume) we synthesise an immediate
  // advance so the user is never stranded on a placeholder. We mark the
  // intro key here because `actions.next()` doesn't emit `step:advance`, so
  // the progress plugin's auto-recording never fires for stubs.
  useTourEvent(
    "step:enter",
    useCallback(
      (event: StepEnterEvent) => {
        if (!isStubStep(event.stepId)) return;
        progressPlugin.add(introKey(event.sectionId));
        actions.next();
      },
      [actions, progressPlugin]
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

  const handleSkipSection = useCallback(() => {
    actions.skipSection();
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
      // engine's current step, also dispatch the configured advance event so
      // the engine's trigger pipeline handles cleanup + section transition
      // (rather than calling `actions.next()` raw, which skips
      // `step:advance` and starves analytics). Idempotent re-records are
      // safe — the plugin's `add` short-circuits on existing keys.
      const nowComplete = progressPlugin.toggle(key);
      if (nowComplete && state.status === "running" && state.sectionId === currentSection.id && state.stepId === item.id) {
        dispatchTourEvent(item.eventName);
      }
    },
    [currentSection, progressPlugin, state]
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
        // Honors the engine's `SectionConfig.skipable` (default true when
        // unset). The intro only opens while a section is active, so reading
        // through `activeStep` is safe — the fallback exists for typing.
        skipable={activeStep?.section.skipable !== false}
        onStart={handleStart}
        onSkipSection={handleSkipSection}
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
                <PulsingRing rect={rect} zIndex={PULSE_RING_Z_INDEX} />
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
          completedItemKeys={completedItemKeys}
          totalItemCount={TOTAL_ITEM_COUNT}
          totalProgress={totalProgress}
          onSelectItem={handleSelectItem}
          onToggleItem={handleToggleItem}
          onSelectSection={handleSelectSection}
          onPrevSection={handlePrevSection}
          onNextSection={handleNextSection}
          onClose={handleDismiss}
        />
      ) : null}
    </TourPortal>
  );
}
