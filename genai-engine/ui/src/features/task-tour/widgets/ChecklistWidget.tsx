import { useCallback, useMemo, type ReactNode } from "react";

import { ChecklistPanel } from "../components/ChecklistPanel";
import { TASK_TOUR_SECTIONS, type TaskTourItem } from "../data";
import { TASK_TOUR_TARGET_LOST_HINTS } from "../tourActions";

import { useActiveTarget, useTour, useTourEngine, useTourPluginStore, type StepRenderContext } from "@/features/tour";
import type { TourStatePlugin } from "@/features/tour";

const TOTAL_ITEM_COUNT = TASK_TOUR_SECTIONS.reduce((sum, s) => sum + Math.max(1, s.items.length), 0);

function itemKey(sectionId: string, itemId: string) {
  return `${sectionId}.${itemId}`;
}

export interface ChecklistWidgetProps {
  /** The shared state plugin instance owned by `TaskTour`. */
  statePlugin: TourStatePlugin;
  /** Optional anchor rect (used when the panel is parked on the resume FAB). */
  panelAnchorRect?: DOMRect | null;
}

/**
 * The interactive checklist panel — mounted only while the engine is on a
 * real step. v1 reads its progress + persisted status from
 * {@link TourStatePlugin} (one Zustand store, replacing v0's separate
 * persistence + progress plugins) and writes via `actions.next()` /
 * `statePlugin.markCompleted`.
 *
 * Stub sections no longer exist in v1, so this widget never has to special-
 * case placeholder steps — intro-only sections are handled by `IntroWidget`
 * and `engine.acknowledgeIntroduction()`.
 */
export function ChecklistWidget({ statePlugin, panelAnchorRect }: ChecklistWidgetProps) {
  const engine = useTourEngine();
  const { state, activeStep, actions } = useTour();
  const completedItemKeys = useTourPluginStore(statePlugin, (s) => s.snapshot.completed);
  const activeTarget = useActiveTarget();

  const currentSectionIndex = state.status === "step" ? state.sectionIndex : 0;
  const currentStepIndex = state.status === "step" ? state.stepIndex : -1;
  const currentSection = TASK_TOUR_SECTIONS[currentSectionIndex];

  const handleDismiss = useCallback(() => actions.dismiss(), [actions]);

  const handleSelectItem = useCallback(
    (item: TaskTourItem, itemIndex: number) => {
      if (state.status !== "step" || !currentSection) return;
      if (state.sectionId === currentSection.id && itemIndex === currentStepIndex) return;
      actions.goTo({ sectionId: currentSection.id, stepId: item.id });
    },
    [actions, currentSection, currentStepIndex, state]
  );

  const handleToggleItem = useCallback(
    (item: TaskTourItem) => {
      if (!currentSection) return;
      const key = itemKey(currentSection.id, item.id);
      const wasComplete = completedItemKeys.has(key);
      if (wasComplete) {
        statePlugin.unmarkCompleted(key);
        return;
      }
      statePlugin.markCompleted(key);
      // If the user just checked off the active step, advance the engine so
      // it leaves the step naturally (which will re-mark via `step:completed`
      // — idempotent against the manual mark above).
      if (state.status === "step" && state.sectionId === currentSection.id && state.stepId === item.id) {
        actions.next();
      }
    },
    [actions, completedItemKeys, currentSection, statePlugin, state]
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

  const activeStepContent = useMemo<ReactNode | null>(() => {
    if (!activeStep) return null;
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

  const activeStepKey = state.status === "step" ? `${state.sectionId}.${state.stepId}` : null;
  const targetLostHint = activeStepKey && !activeTarget ? (TASK_TOUR_TARGET_LOST_HINTS[activeStepKey] ?? null) : null;

  if (state.status !== "step" || !currentSection) return null;

  return (
    <ChecklistPanel
      currentSectionIndex={currentSectionIndex}
      currentItemIndex={currentStepIndex}
      activeStepContent={activeStepContent}
      targetLostHint={targetLostHint}
      completedItemKeys={completedItemKeys}
      totalProgress={totalProgress}
      onSelectItem={handleSelectItem}
      onToggleItem={handleToggleItem}
      onSelectSection={handleSelectSection}
      onPrevSection={handlePrevSection}
      onNextSection={handleNextSection}
      onClose={handleDismiss}
      anchorRect={panelAnchorRect}
    />
  );
}
