import { useCallback, useMemo, type ReactNode } from "react";

import { TASK_TOUR_SECTIONS, type TaskTourItem } from "../data";
import { TASK_TOUR_TARGET_LOST_HINTS } from "../tourActions";

import { useActiveTarget, useTour, useTourEngine, useTourPluginStore, type StepRenderContext, type TourStatePlugin } from "@/features/tour";

const TOTAL_ITEM_COUNT = TASK_TOUR_SECTIONS.reduce((sum, s) => sum + Math.max(1, s.items.length), 0);

function itemKey(sectionId: string, itemId: string) {
  return `${sectionId}.${itemId}`;
}

export interface ChecklistController {
  /**
   * True whenever the tour is running — `intro`, `step`, or `sectionComplete`.
   * The panel stays mounted across all three so it never disappears (and the
   * page never reflows) between sections while a modal is showing.
   */
  isRunning: boolean;
  /** True only on a real step — when the viewport-spanning spotlight backdrop is present. */
  isOnStep: boolean;
  currentSectionIndex: number;
  currentItemIndex: number;
  activeStepContent: ReactNode | null;
  targetLostHint: string | null;
  completedItemKeys: ReadonlySet<string>;
  totalProgress: number;
  onSelectItem: (item: TaskTourItem, itemIndex: number) => void;
  onToggleItem: (item: TaskTourItem) => void;
  onSelectSection: (sectionIndex: number) => void;
  onPrevSection: () => void;
  onNextSection: () => void;
  onClose: () => void;
}

/**
 * Engine-backed data + handlers for the checklist UI. Lifted out of the old
 * floating `ChecklistWidget` so the same controller drives the in-flow
 * {@link import('../components/ChecklistPanelBody').ChecklistPanelBody} inside
 * the docked side panel. Progress + completion come from the shared
 * {@link TourStatePlugin}; navigation goes through the engine's `actions`.
 */
export function useChecklistController(statePlugin: TourStatePlugin): ChecklistController {
  const engine = useTourEngine();
  const { state, activeStep, actions } = useTour();
  const completedItemKeys = useTourPluginStore(statePlugin, (s) => s.snapshot.completed);
  const activeTarget = useActiveTarget();

  // `intro` and `sectionComplete` both carry the section the tour is on, so the
  // panel can show that section's checklist while the modal is up. Only `step`
  // has an active item to highlight.
  const isRunningStatus = state.status === "step" || state.status === "intro" || state.status === "sectionComplete";
  const currentSectionIndex = isRunningStatus ? state.sectionIndex : 0;
  const currentItemIndex = state.status === "step" ? state.stepIndex : -1;
  const currentSection = TASK_TOUR_SECTIONS[currentSectionIndex];

  const onClose = useCallback(() => actions.dismiss(), [actions]);

  const onSelectItem = useCallback(
    (item: TaskTourItem, itemIndex: number) => {
      if (state.status !== "step" || !currentSection) return;
      if (state.sectionId === currentSection.id && itemIndex === currentItemIndex) return;
      actions.goTo({ sectionId: currentSection.id, stepId: item.id });
    },
    [actions, currentSection, currentItemIndex, state]
  );

  const onToggleItem = useCallback(
    (item: TaskTourItem) => {
      if (!currentSection) return;
      const key = itemKey(currentSection.id, item.id);
      const wasComplete = completedItemKeys.has(key);
      if (wasComplete) {
        statePlugin.unmarkCompleted(key);
        return;
      }
      statePlugin.markCompleted(key);
      // If the user just checked off the active step, advance the engine so it
      // leaves the step naturally (which re-marks via `step:completed` —
      // idempotent against the manual mark above).
      if (state.status === "step" && state.sectionId === currentSection.id && state.stepId === item.id) {
        actions.next();
      }
    },
    [actions, completedItemKeys, currentSection, statePlugin, state]
  );

  const onSelectSection = useCallback(
    (sectionIndex: number) => {
      const target = TASK_TOUR_SECTIONS[sectionIndex];
      if (!target) return;
      actions.goTo({ sectionId: target.id });
    },
    [actions]
  );

  const onPrevSection = useCallback(() => {
    const prev = TASK_TOUR_SECTIONS[currentSectionIndex - 1];
    if (prev) actions.goTo({ sectionId: prev.id });
  }, [actions, currentSectionIndex]);

  const onNextSection = useCallback(() => {
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

  return {
    isRunning: isRunningStatus && !!currentSection,
    isOnStep: state.status === "step" && !!currentSection,
    currentSectionIndex,
    currentItemIndex,
    activeStepContent,
    targetLostHint,
    completedItemKeys,
    totalProgress,
    onSelectItem,
    onToggleItem,
    onSelectSection,
    onPrevSection,
    onNextSection,
    onClose,
  };
}
