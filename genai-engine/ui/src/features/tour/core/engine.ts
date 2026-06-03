import type { StoreApi } from "zustand/vanilla";

import { createTourBus } from "./events";
import { matchesRouteWith, resolveRouteWith, toRouteSpec } from "./routes";
import { createTourEngineStore } from "./store";
import { resolveTargetAsync, resolveTargetSync } from "./targets";
import { createDefaultTriggers } from "./triggers";
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
} from "./types";

export interface TourEngineOptions {
  config: TourConfig;
  plugins?: TourPlugin[];
  navigator?: TourNavigator | null;
  resumePosition?: (config: TourConfig) => { sectionId: string; stepId?: string } | null;
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
  const store = createTourEngineStore({
    layers: options.layers,
    initialTriggers: createDefaultTriggers(),
  });
  const bus = createTourBus();
  const middleware: LifecycleMiddleware[] = [];
  const pluginUninstalls: Array<() => void | undefined> = [];
  const prepareHandlers = new Set<(request: PreparationRequest) => void>();

  let activeTriggerCleanups: Array<() => void> = [];
  let enterAbort: AbortController | null = null;
  let navigator: TourNavigator | null = options.navigator ?? null;
  let destroyed = false;
  let exitedStepKey: string | null = null;
  // De-dup memo for target broadcasts (see emitTargetResolution). `undefined` =
  // nothing emitted for the current step yet; `null` = last emitted a loss;
  // Element = last emitted found.
  let lastEmittedTarget: Element | null | undefined = undefined;

  const totalSteps = config.sections.reduce((acc, s) => acc + s.steps.length, 0);

  // ---------------------------------------------------------------------------
  // State helpers
  // ---------------------------------------------------------------------------

  const getState = (): TourState => store.getState().state;
  const activeStepKey = (state: Extract<TourState, { status: "step" }>) =>
    `${state.sectionIndex}:${state.stepIndex}:${state.sectionId}:${state.stepId}`;
  const setState = (next: TourState) => {
    exitedStepKey = null;
    // Any state transition (step change, dismiss, completion) resets the memo so
    // the next step's first resolution always broadcasts.
    lastEmittedTarget = undefined;
    store.getState().setState(next);
  };

  /**
   * Broadcast the resolved target, de-duplicated. `refreshTarget` runs on every
   * DOM mutation while a step is active (via `ActiveTargetRefresh`), so without
   * this an unchanged target would re-emit `target:found` every frame. We emit
   * only when the resolved element actually changes; the memo is reset per step
   * in `setState`, so a freshly-entered step always emits once.
   */
  const emitTargetResolution = (element: Element | null, sectionId: string, stepId: string) => {
    if (lastEmittedTarget !== undefined && lastEmittedTarget === element) return;
    lastEmittedTarget = element;
    if (element) {
      bus.emit("target:found", { tourId: config.id, sectionId, stepId, element });
    } else {
      bus.emit("target:lost", { tourId: config.id, sectionId, stepId });
    }
  };

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

  const isActiveStep = (state: TourState, pos: Position) =>
    state.status === "step" && state.sectionIndex === pos.sectionIndex && state.stepIndex === pos.stepIndex;

  const isActiveSection = (state: TourState, sectionPos: SectionPosition) =>
    (state.status === "step" || state.status === "intro" || state.status === "sectionComplete") && state.sectionIndex === sectionPos.sectionIndex;

  const stateSectionIndex = (state: TourState): number | null =>
    state.status === "step" || state.status === "intro" || state.status === "sectionComplete" ? state.sectionIndex : null;

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
      if (!factory) {
        if (trigger.type === "custom") {
          console.warn("[tour] missing custom trigger factory", {
            tourId: config.id,
            sectionId: ctx.sectionId,
            stepId: ctx.stepId,
            key,
          });
        }
        continue;
      }
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
          void next(cause);
        },
      });
      activeTriggerCleanups.push(cleanup);
    }
  };

  const resolveCurrentTarget = (): Element | null => {
    const current = getState();
    if (current.status !== "step") return null;
    const section = config.sections[current.sectionIndex];
    const step = section.steps[current.stepIndex];
    const resolveQueryHook = (hookId: string): QueryHookResolver | undefined => store.getState().queryHooks.get(hookId);
    return resolveTargetSync(step.target, { resolveQueryHook });
  };

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  const navigateIfNeeded = async (route: string | RouteSpec | undefined, signal: AbortSignal): Promise<boolean> => {
    if (!route || !navigator) return true;
    const spec = toRouteSpec(route);
    const resolved: ResolvedRoute = resolveRouteWith(navigator, spec);
    if (matchesRouteWith(navigator, spec, resolved)) return true;
    bus.emit("navigation:before", { tourId: config.id, from: navigator.getLocation(), to: resolved });
    await navigator.navigate(resolved.full);
    if (signal.aborted) return false;
    if (!matchesRouteWith(navigator, spec, resolved)) return false;
    bus.emit("navigation:after", { tourId: config.id, to: resolved });
    return true;
  };

  // ---------------------------------------------------------------------------
  // Preparation
  // ---------------------------------------------------------------------------

  const runPreparation = (key: string, ctx: StepContext, signal: AbortSignal): Promise<PreparationResult> => {
    return new Promise<PreparationResult>((resolve, reject) => {
      let settled = false;
      const cleanup = () => {
        signal.removeEventListener("abort", onAbort);
      };
      const finish = (result: PreparationResult) => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve(result);
      };
      const fail = (reason: unknown) => {
        if (settled) return;
        settled = true;
        cleanup();
        reject(reason);
      };
      const onAbort = () => finish({ ready: false });

      if (signal.aborted) {
        finish({ ready: false });
        return;
      }

      signal.addEventListener("abort", onAbort, { once: true });

      const handlers = Array.from(prepareHandlers);
      if (handlers.length === 0) {
        // No `<PreparationRunner />` mounted — preparation is best-effort, so
        // resolve as "ready" and continue. The step will fall back to the
        // ordinary target resolution path.
        finish({ ready: true });
        return;
      }
      for (const handler of handlers) {
        handler({ key, stepContext: ctx, resolve: finish, reject: fail, signal });
      }
    });
  };

  // ---------------------------------------------------------------------------
  // Step lifecycle
  // ---------------------------------------------------------------------------

  const completedCausesSet = new Set<StepLeftCause>(["next", "click", "action", "visible", "custom", "complete", "goTo-forward"]);
  const causeForCompleted = (cause: StepLeftCause | undefined): StepCompletedCause | null => {
    if (!cause) return null;
    if (completedCausesSet.has(cause)) return cause as StepCompletedCause;
    return null;
  };

  /**
   * Run a consumer lifecycle hook (section/step `onEnter`/`onExit`) as
   * fire-and-forget: await it and swallow + log any throw so a buggy product
   * hook can't break the engine's transition. Only for void hooks the engine
   * doesn't branch on — navigation, preparation, `skipWhen`, and middleware keep
   * their inline handling because they interleave abort / return control flow.
   */
  const runHook = async (label: string, run: () => void | Promise<void>): Promise<void> => {
    try {
      await run();
    } catch (err) {
      console.error(`[tour] ${label} threw`, err);
    }
  };

  const exitCurrentStep = async (cause: StepLeftCause | undefined): Promise<boolean> => {
    const current = getState();
    if (current.status !== "step") return true;
    const key = activeStepKey(current);
    if (exitedStepKey === key) return false;
    exitedStepKey = key;
    const pos = { sectionIndex: current.sectionIndex, stepIndex: current.stepIndex };
    const ctx = stepContextAt(pos);
    const step = config.sections[pos.sectionIndex].steps[pos.stepIndex];
    detachTriggers();
    if (cause) {
      const completed = causeForCompleted(cause);
      if (completed) bus.emit("step:completed", { ...ctx, cause: completed });
      bus.emit("step:left", { ...ctx, cause });
    }
    await runHook("step.onExit", () => step.onExit?.(ctx));
    return true;
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
      await runHook("section.onEnter", () => section.onEnter?.({ tourId: config.id, sectionId: section.id }));
      if (signal.aborted) return;
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
      const routeMatched = await navigateIfNeeded(route, signal);
      if (!routeMatched) {
        if (!signal.aborted) {
          bus.emit("target:lost", { tourId: config.id, sectionId: section.id, stepId: step.id });
        }
        return;
      }
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
          bus.emit("target:lost", { tourId: config.id, sectionId: section.id, stepId: step.id });
        }
      } catch (err) {
        console.error("[tour] preparation threw", err);
      }
    }

    await runHook("step.onEnter", () => step.onEnter?.(ctx));
    if (signal.aborted) return;

    if (step.skipWhen) {
      try {
        const shouldSkip = await step.skipWhen(ctx);
        if (signal.aborted) return;
        if (shouldSkip) {
          // Auto-skip emits step:left but not step:completed (the user never
          // saw the step) so progress trackers don't double-record it.
          bus.emit("step:left", { ...ctx, cause: "auto-skip" });
          detachTriggers();
          await advanceFromCurrentStep();
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

    emitTargetResolution(element, section.id, step.id);

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
  const goToSection = async (sectionPos: SectionPosition, opts: { skipIntro?: boolean; cause?: StepLeftCause } = {}): Promise<void> => {
    const section = config.sections[sectionPos.sectionIndex];
    const current = getState();
    if (isActiveSection(current, sectionPos)) return;

    if (!(await exitCurrentStep(opts.cause))) return;

    const stateAfterExit = getState();
    const currentSectionIndex = stateSectionIndex(stateAfterExit);
    if (currentSectionIndex !== null && currentSectionIndex !== sectionPos.sectionIndex) {
      const fromSection = config.sections[currentSectionIndex];
      bus.emit("section:exit", {
        tourId: config.id,
        sectionId: fromSection.id,
        sectionIndex: currentSectionIndex,
      });
      await runHook("section.onExit", () => fromSection.onExit?.({ tourId: config.id, sectionId: fromSection.id }));
    }

    if (section.introduction && !opts.skipIntro) {
      bus.emit("section:enter", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: sectionPos.sectionIndex,
      });
      await runHook("section.onEnter", () => section.onEnter?.({ tourId: config.id, sectionId: section.id }));
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
    if (isActiveStep(current, pos)) return;
    const sectionChanging = (current.status !== "step" && current.status !== "intro") || current.sectionIndex !== pos.sectionIndex;
    if (!(await exitCurrentStep(opts.cause))) return;

    if (sectionChanging) {
      const fromIndex = stateSectionIndex(current);
      if (fromIndex !== null) {
        const fromSection = config.sections[fromIndex];
        bus.emit("section:exit", { tourId: config.id, sectionId: fromSection.id, sectionIndex: fromIndex });
        await runHook("section.onExit", () => fromSection.onExit?.({ tourId: config.id, sectionId: fromSection.id }));
      }
    }
    await enterStep(pos, { runSectionEnter: sectionChanging });
  };

  const advanceFromCurrentStep = async (cause?: StepLeftCause): Promise<void> => {
    const pos = getActiveStepPosition();
    if (!pos) return;
    const section = config.sections[pos.sectionIndex];
    if (pos.stepIndex + 1 < section.steps.length) {
      await goToStep({ sectionIndex: pos.sectionIndex, stepIndex: pos.stepIndex + 1 }, { cause });
      return;
    }
    if (config.sectionCompletion === "pause") {
      await completeCurrentSection(pos.sectionIndex, cause);
      return;
    }
    await advanceFromSection(pos.sectionIndex, cause);
  };

  const completeCurrentSection = async (sectionIndex: number, cause?: StepLeftCause): Promise<void> => {
    if (!(await exitCurrentStep(cause))) return;
    const section = config.sections[sectionIndex];
    const nextSection = config.sections[sectionIndex + 1];
    setState({
      status: "sectionComplete",
      sectionId: section.id,
      sectionIndex,
      ...(nextSection ? { nextSectionId: nextSection.id, nextSectionIndex: sectionIndex + 1 } : {}),
    });
    bus.emit("section:complete", {
      tourId: config.id,
      sectionId: section.id,
      sectionIndex,
      ...(nextSection ? { nextSectionId: nextSection.id, nextSectionIndex: sectionIndex + 1 } : {}),
    });
  };

  const advanceFromSection = async (sectionIndex: number, cause?: StepLeftCause): Promise<void> => {
    if (sectionIndex + 1 < config.sections.length) {
      await goToSection({ sectionIndex: sectionIndex + 1 }, { cause });
      return;
    }
    await completeTour(cause);
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

  const completeTour = async (cause?: StepLeftCause): Promise<void> => {
    if (!(await exitCurrentStep(cause))) return;
    const current = getState();
    if (current.status === "step" || current.status === "intro" || current.status === "sectionComplete") {
      const section = config.sections[current.sectionIndex];
      bus.emit("section:exit", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: current.sectionIndex,
      });
      await runHook("section.onExit", () => section.onExit?.({ tourId: config.id, sectionId: section.id }));
    }
    setState({ status: "completed" });
    bus.emit("tour:end", { tourId: config.id, reason: "completed" });
  };

  const skipTour = async (reason: SkipReason): Promise<void> => {
    if (!(await exitCurrentStep("skip"))) return;
    setState({ status: "skipped", reason });
    bus.emit("tour:end", { tourId: config.id, reason: "skipped" });
  };

  // ---------------------------------------------------------------------------
  // Public actions
  // ---------------------------------------------------------------------------

  const start: TourActions["start"] = async (opts) => {
    if (destroyed) return;
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
        await goToStep(stepPos);
        return;
      }
      const sectionPos = findSectionPosition(opts.position.sectionId);
      if (sectionPos) {
        await goToSection(sectionPos);
        return;
      }
    }

    if (opts?.resume) {
      const resumeTarget = options.resumePosition?.(config);
      if (resumeTarget) {
        const stepPos = resumeTarget.stepId ? findStepPosition(resumeTarget.sectionId, resumeTarget.stepId) : null;
        if (stepPos) {
          await goToStep(stepPos);
          return;
        }
        const sectionPos = findSectionPosition(resumeTarget.sectionId);
        if (sectionPos) {
          await goToSection(sectionPos);
          return;
        }
      }
    }

    await goToSection({ sectionIndex: 0 });
  };

  /**
   * Advance to the next step. The internal overload accepts a cause so
   * `attachTriggers`'s callback can forward the trigger's cause verbatim;
   * public callers pass nothing and inherit the default `"next"`.
   */
  const next = async (cause: StepCompletedCause = "next"): Promise<void> => {
    if (destroyed) return;
    const s = getState();
    if (s.status !== "step") return;
    await advanceFromCurrentStep(cause);
  };

  const prev: TourActions["prev"] = async () => {
    if (destroyed) return;
    const s = getState();
    if (s.status !== "step") return;
    const target = retreatFromPosition({ sectionIndex: s.sectionIndex, stepIndex: s.stepIndex });
    if (!target) return;
    await goToStep(target, { cause: "prev" });
  };

  const goTo: TourActions["goTo"] = async (target) => {
    if (destroyed) return;
    const s = getState();
    if (s.status === "idle" || s.status === "completed" || s.status === "skipped") return;

    if (target.stepId) {
      const pos = findStepPosition(target.sectionId, target.stepId);
      if (!pos) return;
      // Forward iff we're on a step and the target is at or past the current
      // position (compare section first, then step). Re-selecting the current
      // step counts as forward (`>=`) to match the documented invariant.
      const isForward =
        s.status === "step" && (pos.sectionIndex !== s.sectionIndex ? pos.sectionIndex > s.sectionIndex : pos.stepIndex >= s.stepIndex);
      const cause: StepLeftCause = isForward ? "goTo-forward" : "goTo-backward";
      await goToStep(pos, { cause });
      return;
    }
    const sectionPos = findSectionPosition(target.sectionId);
    if (!sectionPos) return;
    const currentSectionIndex = stateSectionIndex(s) ?? -1;
    const cause: StepLeftCause = sectionPos.sectionIndex >= currentSectionIndex ? "goTo-forward" : "goTo-backward";
    await goToSection(sectionPos, { cause });
  };

  const skipSection: TourActions["skipSection"] = async () => {
    if (destroyed) return;
    const s = getState();
    if (s.status !== "step" && s.status !== "intro" && s.status !== "sectionComplete") return;
    const section = config.sections[s.sectionIndex];
    if (section.skipable === false) return;
    bus.emit("section:skip", {
      tourId: config.id,
      sectionId: section.id,
      sectionIndex: s.sectionIndex,
    });
    await advanceFromSection(s.sectionIndex, "skipSection");
  };

  const skip: TourActions["skip"] = async (reason = "user") => {
    if (destroyed) return;
    const s = getState();
    if (s.status === "idle" || s.status === "completed" || s.status === "skipped") return;
    await skipTour(reason);
  };

  /**
   * Dismiss preserves the engine position (intro vs step) so a later
   * `resume()` re-enters the same state. Persistence-aware plugins record
   * `dismissed` on the `tour:dismiss` event so the parent component can flip
   * to the FAB branch.
   */
  const dismiss: TourActions["dismiss"] = async () => {
    if (destroyed) return;
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
    } else if (s.status === "intro" || s.status === "sectionComplete") {
      setState({
        status: "dismissed",
        position: {
          sectionId: s.sectionId,
          sectionIndex: s.sectionIndex,
          ...(s.status === "sectionComplete" ? { boundary: "sectionComplete" } : {}),
        },
      });
    } else {
      return;
    }
    bus.emit("tour:dismiss", { tourId: config.id });
  };

  const resume: TourActions["resume"] = async () => {
    if (destroyed) return;
    const s = getState();
    if (s.status !== "dismissed") return;
    bus.emit("tour:resume", { tourId: config.id });
    if (s.position.boundary === "sectionComplete") {
      const section = config.sections[s.position.sectionIndex];
      const nextSection = config.sections[s.position.sectionIndex + 1];
      if (!section) return;
      setState({
        status: "sectionComplete",
        sectionId: section.id,
        sectionIndex: s.position.sectionIndex,
        ...(nextSection ? { nextSectionId: nextSection.id, nextSectionIndex: s.position.sectionIndex + 1 } : {}),
      });
      return;
    }
    if (s.position.stepId && s.position.stepIndex !== undefined) {
      await goToStep({ sectionIndex: s.position.sectionIndex, stepIndex: s.position.stepIndex });
      return;
    }
    await goToSection({ sectionIndex: s.position.sectionIndex });
  };

  const acknowledgeIntroduction: TourActions["acknowledgeIntroduction"] = async () => {
    if (destroyed) return;
    const s = getState();
    if (s.status !== "intro") return;
    const section = config.sections[s.sectionIndex];
    bus.emit("section:intro:acknowledge", { tourId: config.id, sectionId: s.sectionId });
    if (!section.steps.length) {
      await advanceFromSection(s.sectionIndex);
      return;
    }
    await enterStep({ sectionIndex: s.sectionIndex, stepIndex: 0 }, { runSectionEnter: false });
  };

  const continueFromSectionComplete: TourActions["continueFromSectionComplete"] = async () => {
    if (destroyed) return;
    const s = getState();
    if (s.status !== "sectionComplete") return;
    await advanceFromSection(s.sectionIndex);
  };

  const emitAction: TourActions["emitAction"] = (name) => {
    bus.emit("action:emit", { tourId: config.id, name });
  };

  const refreshTarget: TourActions["refreshTarget"] = () => {
    if (destroyed) return;
    const current = getState();
    if (current.status !== "step") return;
    const element = resolveCurrentTarget();
    emitTargetResolution(element, current.sectionId, current.stepId);
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
    destroyed = true;
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
    continueFromSectionComplete,
    refreshTarget,
    emitAction,
  } satisfies TourEngine;
}

function normalizeAdvance(advance?: AdvanceTrigger | AdvanceTrigger[]): AdvanceTrigger[] {
  if (!advance) return [{ type: "manual" }];
  return Array.isArray(advance) ? advance : [advance];
}

// Re-export for downstream typing convenience.
export type { SectionConfig, StepConfig };
