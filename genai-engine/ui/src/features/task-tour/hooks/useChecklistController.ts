import { useDebouncer } from "@tanstack/react-pacer";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { TASK_TOUR_SECTIONS, type TaskTourItem } from "../data";
import { dismissOverlay } from "../dismissOverlay";
import { itemKey, TASK_TOUR_TOTAL_UNITS } from "../progress";
import { DEFAULT_OCCLUSION_HINT, type OcclusionHint, TASK_TOUR_OCCLUSION_HINTS, TASK_TOUR_TARGET_LOST_HINTS } from "../tourActions";

import {
  useActiveTarget,
  useTargetOcclusion,
  useTour,
  useTourEngine,
  useTourPluginStore,
  type StepRenderContext,
  type TourStatePlugin,
} from "@/features/tour";

/**
 * Grace period before a missing target surfaces its "target lost" hint. Clicks
 * inside an active step routinely detach and re-attach the highlighted node for
 * a frame or two (list re-renders, drawer swaps), which momentarily resolves the
 * target to null. Without this delay the red hint copy flashes on every such
 * click (UP-4505). A genuinely missing target stays null past the window and the
 * hint still appears.
 */
const TARGET_LOST_HINT_DELAY_MS = 200;

/**
 * Returns true only after `active` has stayed true continuously for `delayMs`.
 * Flips back to false immediately when `active` becomes false, so the hint
 * disappears the instant the target re-resolves — only the lost→shown edge is
 * debounced (via TanStack Pacer), never shown→cleared.
 */
export function useDelayedFlag(active: boolean, delayMs: number): boolean {
  const [flag, setFlag] = useState(false);
  // Pacer debounces the trailing edge of `maybeExecute`, so a transient `active`
  // blip shorter than `delayMs` is cancelled before it can flip the flag.
  const showDebouncer = useDebouncer(setFlag, { wait: delayMs });

  useEffect(() => {
    if (active) {
      showDebouncer.maybeExecute(true);
    } else {
      // Drop any pending show and clear immediately — no delay on this edge.
      showDebouncer.cancel();
      setFlag(false);
    }
  }, [active, showDebouncer]);

  return flag;
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
  /** Set when the active step's target is in the DOM but covered by another surface. */
  occlusionHint: OcclusionHint | null;
  /** Close registered occluders, bring the target into view, and re-test occlusion. */
  onRecoverOcclusion: () => void;
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
  const occlusion = useTargetOcclusion();

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
    if (TASK_TOUR_TOTAL_UNITS === 0) return 0;
    return completedItemKeys.size / TASK_TOUR_TOTAL_UNITS;
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
  // Debounce the lost→shown edge so a transient target swap on click doesn't
  // flash the hint; see {@link useDelayedFlag} / UP-4505.
  const targetMissing = useDelayedFlag(activeStepKey != null && !activeTarget, TARGET_LOST_HINT_DELAY_MS);
  const targetLostHint = activeStepKey && targetMissing ? (TASK_TOUR_TARGET_LOST_HINTS[activeStepKey] ?? null) : null;
  // Occlusion is mutually exclusive with target-lost at the source (occlusion
  // only fires when an element resolved; target-lost only when none did).
  const occlusionHint = activeStepKey && occlusion ? (TASK_TOUR_OCCLUSION_HINTS[activeStepKey] ?? DEFAULT_OCCLUSION_HINT) : null;

  const onRecoverOcclusion = useCallback(() => {
    // Close any registered occluder, generically dismiss the covering surface
    // (standard MUI modals/drawers the tour never registered), bring the target
    // into view, then re-test so the affordance clears if it worked.
    actions.reconcileActiveSurfaces();
    dismissOverlay(occlusion?.occluder ?? null);
    const element = occlusion?.element;
    if (element && typeof element.scrollIntoView === "function") {
      const reducedMotion = typeof window !== "undefined" && Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
      element.scrollIntoView({ block: "center", behavior: reducedMotion ? "auto" : "smooth" });
    }
    actions.recheckOcclusion();
  }, [actions, occlusion]);

  return {
    isRunning: isRunningStatus && !!currentSection,
    isOnStep: state.status === "step" && !!currentSection,
    currentSectionIndex,
    currentItemIndex,
    activeStepContent,
    targetLostHint,
    occlusionHint,
    onRecoverOcclusion,
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
