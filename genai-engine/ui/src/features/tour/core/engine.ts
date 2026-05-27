import type { StoreApi } from "zustand/vanilla";

import { createTourBus } from "./events";
import { matchesRouteWith, resolveRouteWith, toRouteSpec } from "./routes";
import { createTourEngineStore } from "./store";
import { resolveTargetAsync, resolveTargetSync } from "./targets";
import { createDefaultTriggerRegistry } from "./triggers";
import type {
  AdvanceTrigger,
  HighlightRenderer,
  LifecycleMiddleware,
  PreparationHook,
  PreparationResult,
  QueryHookResolver,
  ResolvedRoute,
  RouteSpec,
  SectionConfig,
  SkipReason,
  StepCompletedCause,
  StepConfig,
  StepContext,
  StepLeftCause,
  TourActions,
  TourBus,
  TourConfig,
  TourEngineStore,
  TourNavigator,
  TourPlugin,
  TourState,
  TriggerFactory,
} from "./types";

export interface TourEngineOptions {
  config: TourConfig;
  plugins?: TourPlugin[];
  navigator?: TourNavigator | null;
  /**
   * Optional layer-token overrides applied at store construction. Useful when
   * a consumer wants to push specific shapes (e.g. lower the spotlight below
   * a fullscreen modal) without authoring a plugin.
   */
  layers?: Record<string, number>;
}

export interface TourEngine extends TourActions {
  readonly config: TourConfig;
  readonly store: StoreApi<TourEngineStore>;
  /** Convenience: subscribe to the engine state slice with referential stability. */
  subscribe: (listener: () => void) => () => void;
  getState: () => TourState;
  bus: TourBus;
  on: TourBus["on"];
  off: TourBus["off"];
  setNavigator: (navigator: TourNavigator | null) => void;
  /** Returns the highlight renderer registered for `key`, if any. */
  getHighlight: (key: string) => HighlightRenderer | undefined;
  /** Returns the queryHook resolver registered for `hookId`, if any. */
  getQueryHook: (hookId: string) => QueryHookResolver | undefined;
  /** Returns the preparation hook registered for `key`, if any. */
  getPreparation: (key: string) => PreparationHook | undefined;
  /**
   * The engine signals a registered preparation hook should now mount by
   * calling this. The runner widget subscribes; it's the only way the engine
   * communicates "load this prep hook now" to React (engine code can't
   * mount components itself).
   */
  onPrepareRequested: (handler: (request: PreparationRequest) => void) => () => void;
  destroy: () => void;
}

/**
 * The engine emits these when a step declares `prepare: { key }`. The
 * `<PreparationRunner />` widget mounts the registered hook on receiving the
 * request and resolves the engine's promise once the hook returns
 * `{ ready: true }`.
 */
export interface PreparationRequest {
  key: string;
  stepContext: StepContext;
  resolve: (result: PreparationResult) => void;
  reject: (reason: unknown) => void;
  signal: AbortSignal;
}

interface Position {
  sectionIndex: number;
  stepIndex: number;
}

interface SectionPosition {
  sectionIndex: number;
}

export function createTourEngine(options: TourEngineOptions): TourEngine {
  const { config } = options;
  const triggersRegistry = createDefaultTriggerRegistry();
  const initialTriggers: Record<string, TriggerFactory> = {};
  for (const key of ["manual", "click", "visible", "action"] as const) {
    const factory = triggersRegistry.get(key);
    if (factory) initialTriggers[key] = factory;
  }
  const store = createTourEngineStore({
    layers: options.layers,
    initialTriggers,
  });
  const bus = createTourBus();
  const middleware: LifecycleMiddleware[] = [];
  const pluginUninstalls: Array<() => void | undefined> = [];
  const prepareHandlers = new Set<(request: PreparationRequest) => void>();

  let activeTriggerCleanups: Array<() => void> = [];
  let enterAbort: AbortController | null = null;
  let navigator: TourNavigator | null = options.navigator ?? null;

  const totalSteps = config.sections.reduce((acc, s) => acc + s.steps.length, 0);

  // ---------------------------------------------------------------------------
  // State helpers
  // ---------------------------------------------------------------------------

  const getState = (): TourState => store.getState().state;
  const setState = (next: TourState) => store.getState().setState(next);

  const stepContextAt = (pos: Position): StepContext => {
    let globalStepIndex = 0;
    for (let i = 0; i < pos.sectionIndex; i++) {
      globalStepIndex += config.sections[i].steps.length;
    }
    globalStepIndex += pos.stepIndex;
    const section = config.sections[pos.sectionIndex];
    const step = section.steps[pos.stepIndex];
    return {
      tourId: config.id,
      sectionId: section.id,
      stepId: step.id,
      index: {
        sectionIndex: pos.sectionIndex,
        stepIndex: pos.stepIndex,
        globalStepIndex,
        totalSteps,
      },
    };
  };

  const findStepPosition = (sectionId: string, stepId: string): Position | null => {
    const sectionIndex = config.sections.findIndex((s) => s.id === sectionId);
    if (sectionIndex < 0) return null;
    const section = config.sections[sectionIndex];
    const stepIndex = section.steps.findIndex((s) => s.id === stepId);
    if (stepIndex < 0) return null;
    return { sectionIndex, stepIndex };
  };

  const findSectionPosition = (sectionId: string): SectionPosition | null => {
    const sectionIndex = config.sections.findIndex((s) => s.id === sectionId);
    if (sectionIndex < 0) return null;
    return { sectionIndex };
  };

  const getActiveStepPosition = (): Position | null => {
    const s = getState();
    return s.status === "step" ? { sectionIndex: s.sectionIndex, stepIndex: s.stepIndex } : null;
  };

  // ---------------------------------------------------------------------------
  // Plugins
  // ---------------------------------------------------------------------------

  for (const plugin of options.plugins ?? []) {
    const cleanup = plugin.install({
      tourId: config.id,
      store,
      bus,
      registerTrigger: (key, factory) => store.getState().registerTrigger(key, factory),
      registerHighlight: (key, renderer) => store.getState().registerHighlight(key, renderer),
      registerPreparation: (key, hook) => store.getState().registerPreparation(key, hook),
      registerQueryHook: (hookId, resolver) => store.getState().registerQueryHook(hookId, resolver),
      registerLayer: (name, z) => store.getState().setLayer(name, z),
      use: (mw) => middleware.push(mw),
    });
    if (cleanup) pluginUninstalls.push(cleanup);
  }

  // ---------------------------------------------------------------------------
  // Trigger management
  // ---------------------------------------------------------------------------

  const detachTriggers = () => {
    for (const cleanup of activeTriggerCleanups) cleanup();
    activeTriggerCleanups = [];
  };

  const attachTriggers = (step: StepConfig, ctx: StepContext, targetElement: Element | null) => {
    detachTriggers();
    const list = normalizeAdvance(step.advanceOn);
    const triggers = store.getState().triggers;
    for (const trigger of list) {
      const key = trigger.type === "custom" ? trigger.key : trigger.type;
      const factory = triggers.get(key);
      if (!factory) continue;
      const cleanup = factory({
        step,
        stepContext: ctx,
        targetElement,
        bus,
        trigger,
        advance: (cause) => {
          const s = getState();
          if (s.status !== "step") return;
          if (s.sectionId !== ctx.sectionId || s.stepId !== ctx.stepId) return;
          next(cause);
        },
      });
      activeTriggerCleanups.push(cleanup);
    }
  };

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  const navigateIfNeeded = async (route: string | RouteSpec | undefined, signal: AbortSignal): Promise<void> => {
    if (!route || !navigator) return;
    const spec = toRouteSpec(route);
    const resolved: ResolvedRoute = resolveRouteWith(navigator, spec);
    if (matchesRouteWith(navigator, spec, resolved)) return;
    bus.emit("navigation:before", { tourId: config.id, from: navigator.getLocation(), to: resolved });
    await navigator.navigate(resolved.full);
    if (signal.aborted) return;
    bus.emit("navigation:after", { tourId: config.id, to: resolved });
  };

  // ---------------------------------------------------------------------------
  // Preparation
  // ---------------------------------------------------------------------------

  const runPreparation = (key: string, ctx: StepContext, signal: AbortSignal): Promise<PreparationResult> => {
    return new Promise<PreparationResult>((resolve, reject) => {
      const handlers = Array.from(prepareHandlers);
      if (handlers.length === 0) {
        // No `<PreparationRunner />` mounted — preparation is best-effort, so
        // resolve as "ready" and continue. The step will fall back to the
        // ordinary target resolution path.
        resolve({ ready: true });
        return;
      }
      for (const handler of handlers) {
        handler({ key, stepContext: ctx, resolve, reject, signal });
      }
    });
  };

  // ---------------------------------------------------------------------------
  // Step lifecycle
  // ---------------------------------------------------------------------------

  const completedCausesSet = new Set<StepLeftCause>(["next", "click", "action", "visible", "custom", "complete"]);
  const causeForCompleted = (cause: StepLeftCause | undefined): StepCompletedCause | null => {
    if (!cause) return null;
    if (completedCausesSet.has(cause)) return cause as StepCompletedCause;
    return null;
  };

  const exitCurrentStep = async (cause: StepLeftCause | undefined) => {
    const pos = getActiveStepPosition();
    if (!pos) return;
    const ctx = stepContextAt(pos);
    const step = config.sections[pos.sectionIndex].steps[pos.stepIndex];
    detachTriggers();
    if (cause) {
      const completed = causeForCompleted(cause);
      if (completed) bus.emit("step:completed", { ...ctx, cause: completed });
      bus.emit("step:left", { ...ctx, cause });
    }
    if (step.onExit) {
      try {
        await step.onExit(ctx);
      } catch (err) {
        console.error("[tour] step.onExit threw", err);
      }
    }
  };

  const enterStep = async (pos: Position, opts: { runSectionEnter: boolean } = { runSectionEnter: false }): Promise<void> => {
    enterAbort?.abort();
    const controller = new AbortController();
    enterAbort = controller;
    const signal = controller.signal;

    const section = config.sections[pos.sectionIndex];
    const step = section.steps[pos.stepIndex];
    const ctx = stepContextAt(pos);

    if (opts.runSectionEnter) {
      bus.emit("section:enter", { tourId: config.id, sectionId: section.id, sectionIndex: pos.sectionIndex });
      if (section.onEnter) {
        try {
          await section.onEnter({ tourId: config.id, sectionId: section.id });
        } catch (err) {
          console.error("[tour] section.onEnter threw", err);
        }
        if (signal.aborted) return;
      }
    }

    setState({
      status: "step",
      sectionId: section.id,
      stepId: step.id,
      sectionIndex: pos.sectionIndex,
      stepIndex: pos.stepIndex,
      globalStepIndex: ctx.index.globalStepIndex,
      totalSteps,
    });

    for (const mw of middleware) {
      try {
        await mw(ctx);
      } catch (err) {
        console.error("[tour] middleware threw", err);
      }
      if (signal.aborted) return;
    }

    const route = step.route ?? (pos.stepIndex === 0 ? section.route : undefined);
    try {
      await navigateIfNeeded(route, signal);
    } catch (err) {
      console.error("[tour] navigation failed", err);
    }
    if (signal.aborted) return;

    if (step.prepare) {
      try {
        const result = await runPreparation(step.prepare.key, ctx, signal);
        if (signal.aborted) return;
        if (!result.ready) {
          // Prep hook reported "not ready" — surface as target-lost so the
          // checklist hint takes over.
          bus.emit("target:lost", { stepId: step.id });
        }
      } catch (err) {
        console.error("[tour] preparation threw", err);
      }
    }

    if (step.onEnter) {
      try {
        await step.onEnter(ctx);
      } catch (err) {
        console.error("[tour] step.onEnter threw", err);
      }
      if (signal.aborted) return;
    }

    if (step.skipWhen) {
      try {
        const shouldSkip = await step.skipWhen(ctx);
        if (signal.aborted) return;
        if (shouldSkip) {
          // Auto-skip emits step:left but not step:completed (the user never
          // saw the step) so progress trackers don't double-record it.
          bus.emit("step:left", { ...ctx, cause: "auto-skip" });
          detachTriggers();
          await advanceFromCurrentStep("auto-skip");
          return;
        }
      } catch (err) {
        console.error("[tour] step.skipWhen threw", err);
      }
    }

    const resolveQueryHook = (hookId: string): QueryHookResolver | undefined => store.getState().queryHooks.get(hookId);
    let element: Element | null = resolveTargetSync(step.target, { resolveQueryHook });
    if (!element && step.awaitTarget) {
      element = await resolveTargetAsync(step.target, {
        timeoutMs: step.awaitTarget.timeoutMs ?? 0,
        signal,
        resolveQueryHook,
      });
    }
    if (signal.aborted) return;

    if (element) {
      bus.emit("target:found", { stepId: step.id, element });
    } else {
      bus.emit("target:lost", { stepId: step.id });
    }

    bus.emit("step:enter", { ...ctx, rect: element?.getBoundingClientRect() ?? null });
    attachTriggers(step, ctx, element);

    // Auto-complete fallback (e.g. for transitional steps without a real
    // target — we schedule a one-shot `next("complete")` after `afterMs`).
    if (step.fallback?.kind === "auto-complete" && !element) {
      const timer = window.setTimeout(() => {
        const s = getState();
        if (s.status !== "step") return;
        if (s.sectionId !== ctx.sectionId || s.stepId !== ctx.stepId) return;
        next("complete");
      }, step.fallback.afterMs);
      activeTriggerCleanups.push(() => window.clearTimeout(timer));
    }
  };

  /**
   * Move the engine to the section at `pos`. If the section has an intro and
   * the engine is entering it for the first time (or we explicitly want the
   * intro re-shown on resume), we switch to `status: "intro"` and emit
   * `section:intro:show`. Otherwise we enter the first step directly.
   *
   * Sections with no steps are entered through the intro state machine only —
   * once acknowledged we advance to the next section, eliminating the v0
   * stub-step hack.
   */
  const goToSection = async (
    sectionPos: SectionPosition,
    opts: { skipIntro?: boolean; cause?: StepLeftCause } = {}
  ): Promise<void> => {
    const section = config.sections[sectionPos.sectionIndex];

    await exitCurrentStep(opts.cause);

    const current = getState();
    const currentSectionIndex =
      current.status === "step" || current.status === "intro" ? current.sectionIndex : null;
    if (currentSectionIndex !== null && currentSectionIndex !== sectionPos.sectionIndex) {
      const fromSection = config.sections[currentSectionIndex];
      bus.emit("section:exit", {
        tourId: config.id,
        sectionId: fromSection.id,
        sectionIndex: currentSectionIndex,
      });
      if (fromSection.onExit) {
        try {
          await fromSection.onExit({ tourId: config.id, sectionId: fromSection.id });
        } catch (err) {
          console.error("[tour] section.onExit threw", err);
        }
      }
    }

    if (section.introduction && !opts.skipIntro) {
      bus.emit("section:enter", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: sectionPos.sectionIndex,
      });
      if (section.onEnter) {
        try {
          await section.onEnter({ tourId: config.id, sectionId: section.id });
        } catch (err) {
          console.error("[tour] section.onEnter threw", err);
        }
      }
      setState({
        status: "intro",
        sectionId: section.id,
        sectionIndex: sectionPos.sectionIndex,
      });
      bus.emit("section:intro:show", { tourId: config.id, sectionId: section.id });
      return;
    }

    if (!section.steps.length) {
      // No intro AND no steps — degenerate section; advance straight past.
      await advanceFromSection(sectionPos.sectionIndex);
      return;
    }

    await enterStep({ sectionIndex: sectionPos.sectionIndex, stepIndex: 0 }, { runSectionEnter: !section.introduction });
  };

  const goToStep = async (pos: Position, opts: { cause?: StepLeftCause } = {}): Promise<void> => {
    const current = getState();
    const sectionChanging =
      (current.status !== "step" && current.status !== "intro") ||
      current.sectionIndex !== pos.sectionIndex;
    await exitCurrentStep(opts.cause);

    if (sectionChanging) {
      const fromIndex =
        current.status === "step" || current.status === "intro" ? current.sectionIndex : null;
      if (fromIndex !== null) {
        const fromSection = config.sections[fromIndex];
        bus.emit("section:exit", { tourId: config.id, sectionId: fromSection.id, sectionIndex: fromIndex });
        if (fromSection.onExit) {
          try {
            await fromSection.onExit({ tourId: config.id, sectionId: fromSection.id });
          } catch (err) {
            console.error("[tour] section.onExit threw", err);
          }
        }
      }
    }
    await enterStep(pos, { runSectionEnter: sectionChanging });
  };

  const advanceFromCurrentStep = async (cause: StepLeftCause): Promise<void> => {
    const pos = getActiveStepPosition();
    if (!pos) return;
    const section = config.sections[pos.sectionIndex];
    if (pos.stepIndex + 1 < section.steps.length) {
      await goToStep({ sectionIndex: pos.sectionIndex, stepIndex: pos.stepIndex + 1 }, { cause });
      return;
    }
    await advanceFromSection(pos.sectionIndex, cause);
  };

  const advanceFromSection = async (sectionIndex: number, cause?: StepLeftCause): Promise<void> => {
    if (sectionIndex + 1 < config.sections.length) {
      await goToSection({ sectionIndex: sectionIndex + 1 }, { cause });
      return;
    }
    await completeTour(cause ?? "complete");
  };

  const retreatFromPosition = (pos: Position): Position | null => {
    if (pos.stepIndex > 0) {
      return { sectionIndex: pos.sectionIndex, stepIndex: pos.stepIndex - 1 };
    }
    // Walk back to the previous section's last step; if the previous
    // section has no steps (intro-only), retreat further. Returns null if
    // we hit the start of the tour.
    for (let i = pos.sectionIndex - 1; i >= 0; i--) {
      const prev = config.sections[i];
      if (prev.steps.length) return { sectionIndex: i, stepIndex: prev.steps.length - 1 };
    }
    return null;
  };

  const completeTour = async (cause: StepLeftCause = "complete"): Promise<void> => {
    await exitCurrentStep(cause);
    const current = getState();
    if (current.status === "step" || current.status === "intro") {
      const section = config.sections[current.sectionIndex];
      bus.emit("section:exit", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: current.sectionIndex,
      });
      if (section.onExit) {
        try {
          await section.onExit({ tourId: config.id, sectionId: section.id });
        } catch (err) {
          console.error("[tour] section.onExit threw", err);
        }
      }
    }
    setState({ status: "completed" });
    bus.emit("tour:end", { tourId: config.id, reason: "completed" });
  };

  const skipTour = async (reason: SkipReason): Promise<void> => {
    await exitCurrentStep("skip");
    setState({ status: "skipped", reason });
    bus.emit("tour:end", { tourId: config.id, reason: "skipped" });
  };

  // ---------------------------------------------------------------------------
  // Public actions
  // ---------------------------------------------------------------------------

  const start: TourActions["start"] = (opts) => {
    enterAbort?.abort();
    detachTriggers();
    if (!config.sections.length) {
      setState({ status: "completed" });
      return;
    }

    bus.emit("tour:start", { tourId: config.id });

    if (opts?.position) {
      const stepPos = opts.position.stepId ? findStepPosition(opts.position.sectionId, opts.position.stepId) : null;
      if (stepPos) {
        void goToStep(stepPos);
        return;
      }
      const sectionPos = findSectionPosition(opts.position.sectionId);
      if (sectionPos) {
        void goToSection(sectionPos);
        return;
      }
    }

    void goToSection({ sectionIndex: 0 });
  };

  /**
   * Advance to the next step. The internal overload accepts a cause so
   * `attachTriggers`'s callback can forward the trigger's cause verbatim;
   * public callers pass nothing and inherit the default `"next"`.
   */
  const next = (cause: StepCompletedCause = "next"): void => {
    const s = getState();
    if (s.status !== "step") return;
    void advanceFromCurrentStep(cause);
  };

  const prev: TourActions["prev"] = () => {
    const s = getState();
    if (s.status !== "step") return;
    const target = retreatFromPosition({ sectionIndex: s.sectionIndex, stepIndex: s.stepIndex });
    if (!target) return;
    void goToStep(target, { cause: "prev" });
  };

  const goTo: TourActions["goTo"] = (target) => {
    const s = getState();
    if (s.status === "idle" || s.status === "completed" || s.status === "skipped") return;

    if (target.stepId) {
      const pos = findStepPosition(target.sectionId, target.stepId);
      if (!pos) return;
      const cause: StepLeftCause = s.status === "step" && pos.sectionIndex * 10000 + pos.stepIndex >= s.sectionIndex * 10000 + s.stepIndex ? "goTo-forward" : "goTo-backward";
      void goToStep(pos, { cause });
      return;
    }
    const sectionPos = findSectionPosition(target.sectionId);
    if (!sectionPos) return;
    const currentSectionIndex = s.status === "step" || s.status === "intro" ? s.sectionIndex : -1;
    const cause: StepLeftCause = sectionPos.sectionIndex >= currentSectionIndex ? "goTo-forward" : "goTo-backward";
    void goToSection(sectionPos, { cause });
  };

  const skipSection: TourActions["skipSection"] = () => {
    const s = getState();
    if (s.status !== "step" && s.status !== "intro") return;
    const section = config.sections[s.sectionIndex];
    if (section.skipable === false) return;
    bus.emit("section:skip", {
      tourId: config.id,
      sectionId: section.id,
      sectionIndex: s.sectionIndex,
    });
    void advanceFromSection(s.sectionIndex, "skipSection");
  };

  const skip: TourActions["skip"] = (reason = "user") => {
    const s = getState();
    if (s.status === "idle" || s.status === "completed" || s.status === "skipped") return;
    void skipTour(reason);
  };

  /**
   * Dismiss preserves the engine position (intro vs step) so a later
   * `resume()` re-enters the same state. Persistence-aware plugins record
   * `dismissed` on the `tour:dismiss` event so the parent component can flip
   * to the FAB branch.
   */
  const dismiss: TourActions["dismiss"] = () => {
    const s = getState();
    if (s.status === "step") {
      detachTriggers();
      setState({
        status: "dismissed",
        position: {
          sectionId: s.sectionId,
          sectionIndex: s.sectionIndex,
          stepId: s.stepId,
          stepIndex: s.stepIndex,
        },
      });
    } else if (s.status === "intro") {
      setState({
        status: "dismissed",
        position: {
          sectionId: s.sectionId,
          sectionIndex: s.sectionIndex,
        },
      });
    } else {
      return;
    }
    bus.emit("tour:dismiss", { tourId: config.id });
  };

  const resume: TourActions["resume"] = () => {
    const s = getState();
    if (s.status !== "dismissed") return;
    bus.emit("tour:resume", { tourId: config.id });
    if (s.position.stepId && s.position.stepIndex !== undefined) {
      void goToStep({ sectionIndex: s.position.sectionIndex, stepIndex: s.position.stepIndex });
      return;
    }
    void goToSection({ sectionIndex: s.position.sectionIndex });
  };

  const acknowledgeIntroduction: TourActions["acknowledgeIntroduction"] = () => {
    const s = getState();
    if (s.status !== "intro") return;
    const section = config.sections[s.sectionIndex];
    bus.emit("section:intro:acknowledge", { tourId: config.id, sectionId: s.sectionId });
    if (!section.steps.length) {
      void advanceFromSection(s.sectionIndex);
      return;
    }
    void enterStep({ sectionIndex: s.sectionIndex, stepIndex: 0 }, { runSectionEnter: false });
  };

  const emitAction: TourActions["emitAction"] = (name) => {
    bus.emit("action:emit", { tourId: config.id, name });
  };

  // ---------------------------------------------------------------------------
  // Subscription / lifecycle
  // ---------------------------------------------------------------------------

  const subscribe = (listener: () => void) => {
    let prev = getState();
    return store.subscribe((snapshot) => {
      const nextState = snapshot.state;
      if (nextState !== prev) {
        prev = nextState;
        listener();
      }
    });
  };

  const setNavigator = (n: TourNavigator | null) => {
    navigator = n;
  };

  const destroy = () => {
    enterAbort?.abort();
    detachTriggers();
    for (const u of pluginUninstalls) u?.();
    pluginUninstalls.length = 0;
    prepareHandlers.clear();
    bus.all.clear();
  };

  const onPrepareRequested: TourEngine["onPrepareRequested"] = (handler) => {
    prepareHandlers.add(handler);
    return () => {
      prepareHandlers.delete(handler);
    };
  };

  return {
    config,
    store,
    bus,
    on: bus.on.bind(bus),
    off: bus.off.bind(bus),
    getState,
    subscribe,
    setNavigator,
    getHighlight: (key) => store.getState().highlights.get(key),
    getQueryHook: (hookId) => store.getState().queryHooks.get(hookId),
    getPreparation: (key) => store.getState().preparations.get(key),
    onPrepareRequested,
    destroy,
    start,
    next,
    prev,
    goTo,
    skipSection,
    skip,
    dismiss,
    resume,
    acknowledgeIntroduction,
    emitAction,
  } satisfies TourEngine;
}

function normalizeAdvance(advance?: AdvanceTrigger | AdvanceTrigger[]): AdvanceTrigger[] {
  if (!advance) return [{ type: "manual" }];
  return Array.isArray(advance) ? advance : [advance];
}

// Re-export for downstream typing convenience.
export type { SectionConfig, StepConfig };
