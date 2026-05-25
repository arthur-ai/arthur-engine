import { createTourBus } from "./events";
import { matchesRouteWith, resolveRouteWith, toRouteSpec } from "./routes";
import { resolveTargetAsync, resolveTargetSync } from "./targets";
import { createDefaultTriggerRegistry } from "./triggers";
import type {
  AdvanceTrigger,
  HighlightRenderer,
  LifecycleMiddleware,
  ResolvedRoute,
  RouteSpec,
  SkipReason,
  StepAdvanceCause,
  StepConfig,
  StepContext,
  TourActions,
  TourBus,
  TourConfig,
  TourNavigator,
  TourPlugin,
  TourState,
} from "./types";

export interface TourEngineOptions {
  config: TourConfig;
  plugins?: TourPlugin[];
  navigator?: TourNavigator | null;
}

export interface TourEngine extends TourActions {
  readonly config: TourConfig;
  getState: () => TourState;
  subscribe: (listener: () => void) => () => void;
  bus: TourBus;
  on: TourBus["on"];
  off: TourBus["off"];
  setNavigator: (navigator: TourNavigator | null) => void;
  /**
   * Look up a highlight renderer registered by a plugin via
   * `registerHighlight(key, renderer)`. Returns `undefined` when no plugin
   * has registered for `key`; consumers (typically the React `Spotlight`
   * primitive) should fall back to a sensible default in that case.
   */
  getHighlight: (key: string) => HighlightRenderer | undefined;
  destroy: () => void;
}

interface Position {
  sectionIndex: number;
  stepIndex: number;
}

export function createTourEngine(options: TourEngineOptions): TourEngine {
  const { config } = options;
  const bus = createTourBus();
  const triggers = createDefaultTriggerRegistry();
  const listeners = new Set<() => void>();
  const middleware: LifecycleMiddleware[] = [];
  const pluginUninstalls: Array<() => void | undefined> = [];

  let state: TourState = { status: "idle" };
  let activeTriggerCleanups: Array<() => void> = [];
  let enterAbort: AbortController | null = null;
  let navigator: TourNavigator | null = options.navigator ?? null;
  const highlights = new Map<string, HighlightRenderer>();

  const totalSteps = config.sections.reduce((acc, s) => acc + s.steps.length, 0);

  // ---------------------------------------------------------------------------
  // State helpers
  // ---------------------------------------------------------------------------

  const setState = (next: TourState) => {
    state = next;
    listeners.forEach((l) => l());
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

  const findPosition = (sectionId: string, stepId?: string): Position | null => {
    const sectionIndex = config.sections.findIndex((s) => s.id === sectionId);
    if (sectionIndex < 0) return null;
    const section = config.sections[sectionIndex];
    if (!section.steps.length) return null;
    if (!stepId) return { sectionIndex, stepIndex: 0 };
    const stepIndex = section.steps.findIndex((s) => s.id === stepId);
    if (stepIndex < 0) return null;
    return { sectionIndex, stepIndex };
  };

  const getActivePosition = (): Position | null => {
    if (state.status !== "running" && state.status !== "paused") return null;
    return findPosition(state.sectionId, state.stepId);
  };

  // ---------------------------------------------------------------------------
  // Plugins
  // ---------------------------------------------------------------------------

  for (const plugin of options.plugins ?? []) {
    const cleanup = plugin.install({
      tourId: config.id,
      bus,
      registerTrigger: (key, factory) => triggers.register(key, factory),
      // Custom highlight renderers are stored on the engine and consumed by
      // the React `Spotlight` primitive via `engine.getHighlight(key)`. A
      // step's `highlight: { shape: "custom", key }` then dispatches to the
      // matching renderer; if no plugin has registered for the key,
      // `Spotlight` falls back to its default box cutout.
      registerHighlight: (key, renderer) => {
        highlights.set(key, renderer);
      },
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
        // Triggers report their own cause; `exitCurrentStep` emits the
        // matching `step:advance` event so the source of the exit (`click`,
        // `event`, `visible`, etc.) propagates to plugins/analytics. We
        // pass the trigger's cause through `next()` rather than emitting
        // here to keep every step exit on the same `exitCurrentStep` code
        // path (manual `next/prev/goTo/...` calls also need to emit).
        advance: (triggerType) => {
          if (state.status !== "running") return;
          if (state.sectionId !== ctx.sectionId || state.stepId !== ctx.stepId) return;
          next(triggerType);
        },
      });
      activeTriggerCleanups.push(cleanup);
    }
  };

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  const navigateIfNeeded = async (route: string | RouteSpec | undefined, signal: AbortSignal): Promise<void> => {
    if (!route) return;
    if (!navigator) return;
    const spec = toRouteSpec(route);
    const resolved: ResolvedRoute = resolveRouteWith(navigator, spec);
    if (matchesRouteWith(navigator, spec, resolved)) return;
    bus.emit("navigation:before", {
      tourId: config.id,
      from: navigator.getLocation(),
      to: resolved,
    });
    await navigator.navigate(resolved.full);
    if (signal.aborted) return;
    bus.emit("navigation:after", { tourId: config.id, to: resolved });
  };

  // ---------------------------------------------------------------------------
  // Step lifecycle
  // ---------------------------------------------------------------------------

  /**
   * Leave the active step. When `triggerType` is provided we emit
   * `step:advance` so consumers (analytics, the checklist progress plugin,
   * tests) can treat every exit — whether prompted by an `advanceOn` trigger
   * firing or a programmatic `next/prev/goTo/skipSection/complete/skip`
   * call — as the same "user moved on from this step" signal.
   *
   * Omitting `triggerType` (the default) skips the `step:advance` emission;
   * `start()` uses this when leaving a stale paused step on a fresh start
   * so it does not look like the user just advanced past that step.
   */
  const exitCurrentStep = async (triggerType?: StepAdvanceCause) => {
    const pos = getActivePosition();
    if (!pos) return;
    const ctx = stepContextAt(pos);
    const step = config.sections[pos.sectionIndex].steps[pos.stepIndex];
    detachTriggers();
    if (triggerType) {
      bus.emit("step:advance", { ...ctx, triggerType });
    }
    bus.emit("step:exit", ctx);
    if (step.onExit) {
      try {
        await step.onExit(ctx);
      } catch (err) {
        console.error("[tour] step.onExit threw", err);
      }
    }
  };

  const enterStep = async (pos: Position, options: { runSectionEnter: boolean } = { runSectionEnter: false }) => {
    enterAbort?.abort();
    const controller = new AbortController();
    enterAbort = controller;
    const signal = controller.signal;

    const section = config.sections[pos.sectionIndex];
    const step = section.steps[pos.stepIndex];
    const ctx = stepContextAt(pos);

    if (options.runSectionEnter) {
      bus.emit("section:enter", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: pos.sectionIndex,
      });
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
      status: "running",
      sectionId: section.id,
      stepId: step.id,
      sectionIndex: pos.sectionIndex,
      stepIndex: pos.stepIndex,
      globalStepIndex: ctx.index.globalStepIndex,
      totalSteps,
      introductionPending: false,
    });

    bus.emit("step:before-enter", ctx);
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

    if (step.onEnter) {
      try {
        await step.onEnter(ctx);
      } catch (err) {
        console.error("[tour] step.onEnter threw", err);
      }
      if (signal.aborted) return;
    }

    let element: Element | null = resolveTargetSync(step.target);
    if (!element && step.awaitTarget) {
      element = await resolveTargetAsync(step.target, {
        timeoutMs: step.awaitTarget.timeoutMs ?? 0,
        signal,
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
  };

  /**
   * Move to (sectionIndex, stepIndex). Handles section transitions including
   * the section introduction handshake. `opts.triggerType` propagates the
   * exit cause to `exitCurrentStep` so `step:advance` carries the right
   * signal (`next`, `prev`, `goTo`, `skipSection`, `complete`, `skip`, or
   * one of the `advanceOn` trigger types). Omit it when the move isn't
   * "advancing past the current step" — e.g. the initial `start()` jump
   * from `idle`.
   */
  const goToPosition = async (target: Position, opts: { force?: boolean; triggerType?: StepAdvanceCause } = {}): Promise<void> => {
    const current = getActivePosition();
    const sectionChanging = !current || current.sectionIndex !== target.sectionIndex;

    await exitCurrentStep(opts.triggerType);

    if (sectionChanging && current) {
      const fromSection = config.sections[current.sectionIndex];
      bus.emit("section:exit", {
        tourId: config.id,
        sectionId: fromSection.id,
        sectionIndex: current.sectionIndex,
      });
      if (fromSection.onExit) {
        try {
          await fromSection.onExit({ tourId: config.id, sectionId: fromSection.id });
        } catch (err) {
          console.error("[tour] section.onExit threw", err);
        }
      }
    }

    const section = config.sections[target.sectionIndex];
    const step = section.steps[target.stepIndex];

    // Introduction handshake when newly entering a section that has one.
    if (sectionChanging && section.introduction && !opts.force && target.stepIndex === 0) {
      bus.emit("section:enter", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: target.sectionIndex,
      });
      if (section.onEnter) {
        try {
          await section.onEnter({ tourId: config.id, sectionId: section.id });
        } catch (err) {
          console.error("[tour] section.onEnter threw", err);
        }
      }
      const ctx = stepContextAt(target);
      setState({
        status: "running",
        sectionId: section.id,
        stepId: step.id,
        sectionIndex: target.sectionIndex,
        stepIndex: target.stepIndex,
        globalStepIndex: ctx.index.globalStepIndex,
        totalSteps,
        introductionPending: true,
      });
      bus.emit("section:introduction:show", { tourId: config.id, sectionId: section.id });
      return;
    }

    await enterStep(target, { runSectionEnter: sectionChanging });
  };

  const advanceFromPosition = (pos: Position): Position | "complete" => {
    const section = config.sections[pos.sectionIndex];
    if (pos.stepIndex + 1 < section.steps.length) {
      return { sectionIndex: pos.sectionIndex, stepIndex: pos.stepIndex + 1 };
    }
    if (pos.sectionIndex + 1 < config.sections.length) {
      return { sectionIndex: pos.sectionIndex + 1, stepIndex: 0 };
    }
    return "complete";
  };

  const retreatFromPosition = (pos: Position): Position | null => {
    if (pos.stepIndex > 0) {
      return { sectionIndex: pos.sectionIndex, stepIndex: pos.stepIndex - 1 };
    }
    if (pos.sectionIndex > 0) {
      const prevSection = config.sections[pos.sectionIndex - 1];
      return { sectionIndex: pos.sectionIndex - 1, stepIndex: prevSection.steps.length - 1 };
    }
    return null;
  };

  const completeTour = async (triggerType: StepAdvanceCause = "complete") => {
    await exitCurrentStep(triggerType);
    const pos = getActivePosition();
    if (pos) {
      const section = config.sections[pos.sectionIndex];
      bus.emit("section:exit", {
        tourId: config.id,
        sectionId: section.id,
        sectionIndex: pos.sectionIndex,
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

  const skipTour = async (reason: SkipReason) => {
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
    const target = (opts?.sectionId ? findPosition(opts.sectionId, opts.stepId) : null) ?? ({ sectionIndex: 0, stepIndex: 0 } as Position);

    bus.emit("tour:start", { tourId: config.id });
    void goToPosition(target);
  };

  /**
   * Advance to the next step. The internal overload accepts a `triggerType`
   * so `attachTriggers`'s `advance(triggerType)` callback can forward the
   * trigger's cause (`click`, `event`, `visible`, `custom`, `manual`)
   * verbatim. Public callers pass nothing and inherit the default `"next"`
   * cause used for analytics / progress tracking.
   */
  const next = (triggerType: StepAdvanceCause = "next"): void => {
    if (state.status !== "running" || state.introductionPending) return;
    const pos = getActivePosition();
    if (!pos) return;
    const result = advanceFromPosition(pos);
    if (result === "complete") {
      void completeTour(triggerType);
    } else {
      void goToPosition(result, { triggerType });
    }
  };

  const prev: TourActions["prev"] = () => {
    if (state.status !== "running" || state.introductionPending) return;
    const pos = getActivePosition();
    if (!pos) return;
    const target = retreatFromPosition(pos);
    if (!target) return;
    void goToPosition(target, { triggerType: "prev" });
  };

  const goTo: TourActions["goTo"] = (target) => {
    if (state.status === "idle" || state.status === "completed" || state.status === "skipped") return;
    const pos = findPosition(target.sectionId, target.stepId);
    if (!pos) return;
    void goToPosition(pos, { triggerType: "goTo" });
  };

  const skipSection: TourActions["skipSection"] = () => {
    if (state.status !== "running") return;
    const pos = getActivePosition();
    if (!pos) return;
    const section = config.sections[pos.sectionIndex];
    if (section.skipable === false) return;
    bus.emit("section:skip", {
      tourId: config.id,
      sectionId: section.id,
      sectionIndex: pos.sectionIndex,
    });
    if (pos.sectionIndex + 1 < config.sections.length) {
      void goToPosition({ sectionIndex: pos.sectionIndex + 1, stepIndex: 0 }, { triggerType: "skipSection" });
    } else {
      void completeTour("skipSection");
    }
  };

  const skip: TourActions["skip"] = (reason = "user") => {
    if (state.status === "idle" || state.status === "completed" || state.status === "skipped") return;
    void skipTour(reason);
  };

  const pause: TourActions["pause"] = () => {
    if (state.status !== "running") return;
    detachTriggers();
    setState({
      status: "paused",
      sectionId: state.sectionId,
      stepId: state.stepId,
      introductionPending: state.introductionPending,
    });
    bus.emit("tour:pause", { tourId: config.id });
  };

  const resume: TourActions["resume"] = () => {
    if (state.status !== "paused") return;
    const pos = findPosition(state.sectionId, state.stepId);
    if (!pos) return;
    bus.emit("tour:resume", { tourId: config.id });
    // If the user paused or dismissed while a section intro was open, we
    // need to re-open that intro on resume — `enterStep` would set
    // `introductionPending: false` and silently skip past it. Mirror the
    // intro-handshake branch of `goToPosition` so the intro modal comes
    // back instead of dropping straight onto the first spotlight.
    if (pos.stepIndex === 0 && state.introductionPending) {
      const section = config.sections[pos.sectionIndex];
      if (section.introduction) {
        const step = section.steps[pos.stepIndex];
        const ctx = stepContextAt(pos);
        setState({
          status: "running",
          sectionId: section.id,
          stepId: step.id,
          sectionIndex: pos.sectionIndex,
          stepIndex: pos.stepIndex,
          globalStepIndex: ctx.index.globalStepIndex,
          totalSteps,
          introductionPending: true,
        });
        bus.emit("section:introduction:show", { tourId: config.id, sectionId: section.id });
        return;
      }
    }
    void enterStep(pos, { runSectionEnter: false });
  };

  /**
   * Dismiss is a "soft close" — the user is closing the panel but we want to
   * be able to bring it back. We pause first (preserving the position and
   * the `introductionPending` flag) and then emit `tour:dismiss` so
   * persistence plugins can record the intent. Preserving
   * `introductionPending` matters because section intros carry
   * scenario/marketing copy — if the user dismisses while the intro modal
   * is open, resume should re-show it rather than jump straight to the
   * first spotlight. No-ops outside running/paused.
   */
  const dismiss: TourActions["dismiss"] = () => {
    if (state.status !== "running" && state.status !== "paused") return;
    if (state.status === "running") {
      detachTriggers();
      setState({
        status: "paused",
        sectionId: state.sectionId,
        stepId: state.stepId,
        introductionPending: state.introductionPending,
      });
    }
    bus.emit("tour:dismiss", { tourId: config.id });
  };

  const acknowledgeIntroduction: TourActions["acknowledgeIntroduction"] = () => {
    if (state.status !== "running" || !state.introductionPending) return;
    const pos = findPosition(state.sectionId, state.stepId);
    if (!pos) return;
    bus.emit("section:introduction:acknowledge", {
      tourId: config.id,
      sectionId: state.sectionId,
    });
    void enterStep(pos, { runSectionEnter: false });
  };

  // ---------------------------------------------------------------------------
  // Subscription / lifecycle
  // ---------------------------------------------------------------------------

  const getState = () => state;

  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  };

  const setNavigator = (next: TourNavigator | null) => {
    navigator = next;
  };

  const destroy = () => {
    enterAbort?.abort();
    detachTriggers();
    for (const u of pluginUninstalls) u?.();
    pluginUninstalls.length = 0;
    listeners.clear();
    bus.all.clear();
  };

  return {
    config,
    bus,
    on: bus.on.bind(bus),
    off: bus.off.bind(bus),
    getState,
    subscribe,
    setNavigator,
    getHighlight: (key) => highlights.get(key),
    destroy,
    start,
    next,
    prev,
    goTo,
    skipSection,
    skip,
    pause,
    resume,
    dismiss,
    acknowledgeIntroduction,
  };
}

function normalizeAdvance(advance?: AdvanceTrigger | AdvanceTrigger[]): AdvanceTrigger[] {
  if (!advance) return [{ type: "manual" }];
  return Array.isArray(advance) ? advance : [advance];
}
