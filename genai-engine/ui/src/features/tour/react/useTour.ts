import { useContext, useMemo } from "react";
import { useStore } from "zustand";

import type { TourEngine } from "../core/createTour";
import type { SectionConfig, StepConfig, TourActions, TourConfig, TourEngineStore, TourState } from "../core/types";

import { TourEngineContext } from "./context";

export interface ActiveStep {
  section: SectionConfig;
  step: StepConfig;
  sectionIndex: number;
  stepIndex: number;
  globalStepIndex: number;
  totalSteps: number;
}

export interface UseTourReturn {
  state: TourState;
  config: TourConfig;
  actions: TourActions;
  activeStep: ActiveStep | null;
  activeSection: SectionConfig | null;
}

/**
 * Returns the tour engine bound to the current provider. Throws if used
 * outside `<TourProvider>`.
 */
export function useTourEngine(): TourEngine {
  const engine = useContext(TourEngineContext);
  if (!engine) {
    throw new Error("useTourEngine: must be used inside <TourProvider>");
  }
  return engine;
}

/**
 * Read an arbitrary slice of the engine's Zustand store. Cheap when callers
 * only need one or two fields (e.g. just `layers`).
 *
 * Example:
 * ```ts
 * const completed = useTourStore(s => s.state.status === "completed");
 * ```
 */
export function useTourStore<T>(selector: (state: TourEngineStore) => T): T {
  const engine = useTourEngine();
  return useStore(engine.store, selector);
}

const defaultActionsCache = new WeakMap<TourEngine, TourActions>();
function cachedActions(engine: TourEngine): TourActions {
  let cached = defaultActionsCache.get(engine);
  if (cached) return cached;
  cached = {
    start: engine.start,
    next: engine.next,
    prev: engine.prev,
    goTo: engine.goTo,
    skipSection: engine.skipSection,
    skip: engine.skip,
    dismiss: engine.dismiss,
    resume: engine.resume,
    acknowledgeIntroduction: engine.acknowledgeIntroduction,
    emitAction: engine.emitAction,
  };
  defaultActionsCache.set(engine, cached);
  return cached;
}

/**
 * Convenience aggregator pulling state + config + actions + the derived
 * `activeStep` / `activeSection`. Subscribes via the engine store so React
 * tracks the state slice with referential stability.
 */
export function useTour(): UseTourReturn {
  const engine = useTourEngine();
  const state = useTourStore((s) => s.state);

  const actions = cachedActions(engine);

  const activeStep = useMemo<ActiveStep | null>(() => {
    if (state.status !== "step") return null;
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
    };
  }, [engine, state]);

  const activeSection = useMemo<SectionConfig | null>(() => {
    if (state.status === "step" || state.status === "intro") {
      return engine.config.sections[state.sectionIndex] ?? null;
    }
    return null;
  }, [engine, state]);

  return { state, config: engine.config, actions, activeStep, activeSection };
}

/** Read the current state slice only. Cheaper than `useTour` when actions/config aren't needed. */
export function useTourState(): TourState {
  return useTourStore((s) => s.state);
}
