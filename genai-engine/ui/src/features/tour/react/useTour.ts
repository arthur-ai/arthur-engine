import { useContext, useMemo, useSyncExternalStore } from "react";

import type { TourEngine } from "../core/createTour";
import type { SectionConfig, StepConfig, TourActions, TourConfig, TourState } from "../core/types";

import { TourEngineContext } from "./context";

export interface ActiveStep {
  section: SectionConfig;
  step: StepConfig;
  sectionIndex: number;
  stepIndex: number;
  globalStepIndex: number;
  totalSteps: number;
  introductionPending: boolean;
}

export interface UseTourReturn {
  state: TourState;
  config: TourConfig;
  actions: TourActions;
  activeStep: ActiveStep | null;
}

/**
 * Returns the tour engine bound to the current provider. Throws if used outside
 * `<TourProvider>`. The engine itself is the source of truth and is stable for
 * the provider's lifetime.
 */
export function useTourEngine(): TourEngine {
  const engine = useContext(TourEngineContext);
  if (!engine) {
    throw new Error("useTourEngine: must be used inside <TourProvider>");
  }
  return engine;
}

/**
 * Subscribes to engine state via useSyncExternalStore. Returns the current
 * state, actions, config, and a derived `activeStep` for ergonomics.
 */
export function useTour(): UseTourReturn {
  const engine = useTourEngine();
  const state = useSyncExternalStore(engine.subscribe, engine.getState, engine.getState);

  const actions = useMemo<TourActions>(
    () => ({
      start: engine.start,
      next: engine.next,
      prev: engine.prev,
      goTo: engine.goTo,
      skipSection: engine.skipSection,
      skip: engine.skip,
      pause: engine.pause,
      resume: engine.resume,
      dismiss: engine.dismiss,
      acknowledgeIntroduction: engine.acknowledgeIntroduction,
    }),
    [engine]
  );

  const activeStep = useMemo<ActiveStep | null>(() => {
    if (state.status !== "running") return null;
    const section = engine.config.sections[state.sectionIndex];
    if (!section) return null;
    const step = section.steps[state.stepIndex];
    if (!step) return null;
    return {
      section,
      step,
      sectionIndex: state.sectionIndex,
      stepIndex: state.stepIndex,
      globalStepIndex: state.globalStepIndex,
      totalSteps: state.totalSteps,
      introductionPending: state.introductionPending,
    };
  }, [engine, state]);

  return { state, config: engine.config, actions, activeStep };
}

/**
 * Read-only snapshot of state. Cheaper than `useTour` when actions/config
 * aren't needed (e.g. in companion widgets).
 */
export function useTourState(): TourState {
  const engine = useTourEngine();
  return useSyncExternalStore(engine.subscribe, engine.getState, engine.getState);
}
