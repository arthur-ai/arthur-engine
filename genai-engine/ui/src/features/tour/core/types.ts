import type { Placement } from "@floating-ui/react";
import type { Emitter, EventType } from "mitt";
import type { CSSProperties, ReactNode, RefObject } from "react";
import type { StoreApi } from "zustand/vanilla";

// =============================================================================
// Target resolution
// =============================================================================

/**
 * `queryHook` defers element resolution to a React hook the consumer registers
 * via {@link TourPluginContext.registerQueryHook} (typically driven by the
 * Preparation plugin or product code). This lets a step bind to a live React
 * ref (e.g. the first row of a virtualized table) without relying on a
 * `data-tour-id` attribute reaching the DOM through prop-spread — the
 * underlying root cause of the dogfood P0s on the traces section.
 */
export type TargetSpec =
  | { kind: "selector"; selector: string }
  | { kind: "element"; resolve: () => Element | null }
  | { kind: "ref"; ref: RefObject<Element | null> }
  | { kind: "queryHook"; hookId: string };

// =============================================================================
// Routes / navigation
// =============================================================================

export type SearchInput = Record<string, string | number | boolean | null | undefined> | string | URLSearchParams;

export interface RouteSpec {
  path: string;
  params?: Record<string, string | number>;
  search?: SearchInput;
  hash?: string;
  match?: (resolved: ResolvedRoute, current: TourLocation) => boolean;
}

export interface ResolvedRoute {
  pathname: string;
  search: string;
  hash: string;
  full: string;
}

export interface TourLocation {
  pathname: string;
  search: string;
  hash: string;
}

export interface TourNavigator {
  getLocation: () => TourLocation;
  navigate: (to: string) => Promise<void>;
  resolveRoute?: (spec: RouteSpec) => ResolvedRoute;
  matches?: (resolved: ResolvedRoute, current: TourLocation) => boolean;
}

// =============================================================================
// Advance triggers
// =============================================================================

/**
 * v1's typed action channel — replaces v0's untyped string `event` trigger.
 * Actions flow through the engine mitt bus's `action:emit` event (no
 * `document.dispatchEvent` round-trips). Consumers call
 * `useTourAction()(name)` or `engine.emitAction(name)`.
 */
export type AdvanceTrigger =
  | { type: "manual" }
  | { type: "click"; selector?: string }
  | { type: "visible"; threshold?: number; rootMargin?: string }
  | { type: "action"; name: string }
  | { type: "custom"; key: string; options?: unknown };

// =============================================================================
// Highlight
// =============================================================================

export type BoxHighlight = {
  shape: "box";
  padding?: number;
  radius?: number;
  pulse?: boolean;
};

export type CircleHighlight = {
  shape: "circle";
  padding?: number;
  pulse?: boolean;
};

export type NoHighlight = { shape: "none" };

export type CustomHighlight = {
  shape: "custom";
  key: string;
  padding?: number;
  options?: unknown;
};

export type HighlightSpec = BoxHighlight | CircleHighlight | NoHighlight | CustomHighlight;

// =============================================================================
// Overlay
// =============================================================================

export interface OverlayConfig {
  blockInteraction?: boolean;
  onBackdropClick?: "none" | "next" | "skip" | "dismiss";
  color?: string;
}

export interface StepPopoverConfig {
  placement?: Placement;
  showNext?: boolean;
  nextLabel?: string;
}

// =============================================================================
// Step / section / tour configuration
// =============================================================================

export interface StepIndex {
  sectionIndex: number;
  stepIndex: number;
  globalStepIndex: number;
  totalSteps: number;
}

export interface StepContext {
  tourId: string;
  sectionId: string;
  stepId: string;
  index: StepIndex;
}

export type StepRenderContext = StepContext & {
  actions: TourActions;
};

export interface IntroductionConfig {
  title: string;
  description?: ReactNode;
  primaryActionLabel?: string;
  secondaryActionLabel?: string;
}

/**
 * Missing-target behavior owned by the headless engine. Static hints are a
 * widget concern; consumers can render them from their product UI when
 * `target:lost` fires.
 */
export type StepFallback = { kind: "auto-complete"; afterMs: number };

export interface StepFormPrefill {
  targetId: string;
  value?: string;
  values?: Record<string, unknown>;
  mode?: "replace" | "empty-only";
}

export interface StepConfig {
  id: string;
  target: TargetSpec;
  content: ReactNode | ((ctx: StepRenderContext) => ReactNode);
  placement?: Placement;
  popover?: StepPopoverConfig;
  formPrefill?: StepFormPrefill;
  highlight?: HighlightSpec;
  overlay?: OverlayConfig;
  advanceOn?: AdvanceTrigger | AdvanceTrigger[];
  awaitTarget?: { timeoutMs?: number };
  route?: string | RouteSpec;
  /**
   * Auto-skip predicate evaluated when the engine enters the step. When it
   * returns `true` the engine emits `step:left` with cause `auto-skip` and
   * moves on without firing `step:enter`. Used for empty-state steps that
   * have no meaningful target (e.g. an "Open evaluator" step on a task with
   * zero evaluators).
   */
  skipWhen?: (ctx: StepContext) => boolean | Promise<boolean>;
  /**
   * Reference to a Preparation hook registered via
   * `engineStore.registerPreparation(key, hook)`. The engine mounts the hook
   * (through the `<PreparationRunner />` widget inside `TourHost`) before
   * resolving the target so the prep can wait for lazy chunks / open
   * drawers / etc.
   */
  prepare?: { key: string };
  /**
   * Declarative occluder state for reconcile-on-enter. On every step entry the
   * engine closes every registered occluder NOT named in `open`/`keep`, then
   * opens/asserts those in `open`. Surfaces absent from the registry (not
   * currently mounted) are ignored. O(registry size) per step — one
   * declaration per step, never O(N²) over transitions.
   *
   * Omit the whole key to get the safe default: **close every registered
   * occluder**. Reconcile only acts on the delta — a surface a step declares
   * `open` that is already open is left untouched (never close-reopened), so
   * in-progress user input inside it is preserved.
   */
  surfaces?: {
    /** Occluder ids that must be OPEN for this step. Everything else is closed. */
    open?: Array<{ id: string; args?: unknown }>;
    /**
     * Occluder ids to leave untouched (neither force-closed nor opened) —
     * escape hatch for a surface the step neither needs nor wants disturbed.
     */
    keep?: string[];
  };
  fallback?: StepFallback;
  onEnter?: (ctx: StepContext) => void | Promise<void>;
  onExit?: (ctx: StepContext) => void | Promise<void>;
}

export interface SectionConfig {
  id: string;
  title?: string;
  description?: ReactNode;
  introduction?: IntroductionConfig;
  skipable?: boolean;
  route?: string | RouteSpec;
  /**
   * Sections may have **zero** steps in v1. An intro-only section advances
   * straight from `intro:acknowledge` to the next section's intro/step —
   * the stub-step hack from v0 is gone.
   */
  steps: StepConfig[];
  onEnter?: (ctx: { tourId: string; sectionId: string }) => void | Promise<void>;
  onExit?: (ctx: { tourId: string; sectionId: string }) => void | Promise<void>;
}

export interface TourConfig {
  id: string;
  sections: SectionConfig[];
  /**
   * Controls what happens after the final step in a section completes.
   * - "auto" keeps legacy behavior: immediately enter the next section.
   * - "pause" emits a section-complete state so UI can let the user continue intentionally.
   */
  sectionCompletion?: "auto" | "pause";
}

export function defineTourConfig<const T extends TourConfig>(config: T): T {
  return config;
}

type ConfigSection<TConfig extends TourConfig> = TConfig["sections"][number];
type ConfigStep<TConfig extends TourConfig> = ConfigSection<TConfig>["steps"][number];
type ConfigAdvanceTrigger<TConfig extends TourConfig> =
  NonNullable<ConfigStep<TConfig>["advanceOn"]> extends infer TTrigger ? (TTrigger extends readonly (infer TItem)[] ? TItem : TTrigger) : never;

export type TourSectionId<TConfig extends TourConfig> = ConfigSection<TConfig>["id"];
export type TourStepId<TConfig extends TourConfig> = ConfigStep<TConfig>["id"];
export type TourActionName<TConfig extends TourConfig> =
  Extract<ConfigAdvanceTrigger<TConfig>, { type: "action" }> extends infer TAction ? (TAction extends { name: infer TName } ? TName : never) : never;
export type TourPreparationKey<TConfig extends TourConfig> = NonNullable<ConfigStep<TConfig>["prepare"]>["key"];
export type TourQueryHookId<TConfig extends TourConfig> = Extract<ConfigStep<TConfig>["target"], { kind: "queryHook" }>["hookId"];

// =============================================================================
// State machine
// =============================================================================

/**
 * Position inside the tour. Used by every status that has a "where the user
 * is" pointer. Section-only positions (no stepId) represent an intro that
 * hasn't been acknowledged yet.
 */
export interface TourPosition {
  sectionId: string;
  sectionIndex: number;
  stepId?: string;
  stepIndex?: number;
  boundary?: "sectionComplete";
}

export type SkipReason = "user" | "section" | "programmatic" | "auto-skip";

export type TourState =
  | { status: "idle" }
  | { status: "intro"; sectionId: string; sectionIndex: number }
  | {
      status: "step";
      sectionId: string;
      stepId: string;
      sectionIndex: number;
      stepIndex: number;
      globalStepIndex: number;
      totalSteps: number;
    }
  | {
      status: "sectionComplete";
      sectionId: string;
      sectionIndex: number;
      nextSectionId?: string;
      nextSectionIndex?: number;
    }
  | { status: "dismissed"; position: TourPosition }
  | { status: "completed" }
  | { status: "skipped"; reason: SkipReason };

// =============================================================================
// Actions
// =============================================================================

export interface TourActions {
  /**
   * Begin the tour. `position` is an explicit jump-to. `resume: true` uses
   * the engine's configured `resumePosition` callback when one exists.
   */
  start: (options?: { position?: { sectionId: string; stepId?: string }; resume?: boolean }) => Promise<void>;
  next: () => Promise<void>;
  prev: () => Promise<void>;
  goTo: (target: { sectionId: string; stepId?: string }) => Promise<void>;
  skipSection: () => Promise<void>;
  skip: (reason?: SkipReason) => Promise<void>;
  /**
   * Pause the tour and emit `tour:dismiss`. Engine retains its position so a
   * later `resume()` returns the user to where they left off.
   */
  dismiss: () => Promise<void>;
  /**
   * Resume from `dismissed`. The engine derives the resume target from the
   * dismissed position (intro → re-show intro, step → re-enter step).
   */
  resume: () => Promise<void>;
  acknowledgeIntroduction: () => Promise<void>;
  continueFromSectionComplete: () => Promise<void>;
  /**
   * Re-resolve the active step target and emit a fresh `target:found` /
   * `target:lost` event. Useful when a step opens a modal/popover and the
   * highlight should move from the trigger to the newly mounted surface.
   */
  refreshTarget: () => void;
  /**
   * Re-run occlusion detection on the active step's target and emit a fresh
   * `target:occluded` / `target:revealed` (de-duped). Driven by
   * `ActiveTargetRefresh` after each refresh and by the occlusion-recovery
   * widget after closing occluders. No-op when there's no active step / target.
   */
  recheckOcclusion: () => void;
  /**
   * Re-run occluder reconciliation for the active step (close registered
   * surfaces it doesn't declare open/keep). Reconcile normally runs only on
   * step entry; occlusion recovery calls this to close a registered panel that
   * the user opened mid-step. No-op when there's no active step.
   */
  reconcileActiveSurfaces: () => void;
  /**
   * Emit a typed action onto the engine bus. The `action` trigger listens for
   * matching names and advances the active step. Replaces v0's
   * `dispatchTourEvent(name)` + `document.addEventListener` round-trip.
   */
  emitAction: (name: string) => void;
}

// =============================================================================
// Events
// =============================================================================

export interface SectionEnterEvent {
  tourId: string;
  sectionId: string;
  sectionIndex: number;
}

export type SectionExitEvent = SectionEnterEvent;
export type SectionSkipEvent = SectionEnterEvent;

export interface StepEnterEvent extends StepContext {
  rect: DOMRect | null;
}

/**
 * Forward-progress causes. `step:completed` is emitted only for these — the
 * v0 progress plugin's misuse of `step:advance` for `prev`/`goTo` exits is
 * impossible in v1.
 */
export type StepCompletedCause = "next" | "click" | "action" | "visible" | "custom" | "complete" | "goTo-forward";

/**
 * Step exit causes. `step:left` fires on every exit (including the forward
 * ones — `step:completed` is a strict subset).
 */
export type StepLeftCause =
  | StepCompletedCause
  | "prev"
  | "goTo-backward"
  | "goTo-forward"
  | "skip"
  | "skipSection"
  | "dismiss"
  | "auto-skip"
  | "manual";

export interface StepCompletedEvent extends StepContext {
  cause: StepCompletedCause;
}

export interface StepLeftEvent extends StepContext {
  cause: StepLeftCause;
}

export interface NavigationBeforeEvent {
  tourId: string;
  from: TourLocation;
  to: ResolvedRoute;
}

export interface NavigationAfterEvent {
  tourId: string;
  to: ResolvedRoute;
}

export interface ActionEmitEvent {
  tourId: string;
  name: string;
}

export interface TourEvents extends Record<EventType, unknown> {
  "tour:start": { tourId: string };
  "tour:end": { tourId: string; reason: "completed" | "skipped" };
  "tour:dismiss": { tourId: string };
  "tour:resume": { tourId: string };
  "section:enter": SectionEnterEvent;
  "section:exit": SectionExitEvent;
  "section:skip": SectionSkipEvent;
  "section:complete": SectionEnterEvent & { nextSectionId?: string; nextSectionIndex?: number };
  "section:intro:show": { tourId: string; sectionId: string };
  "section:intro:acknowledge": { tourId: string; sectionId: string };
  "step:enter": StepEnterEvent;
  /**
   * Emitted only when the user / engine advances *forward* past the step
   * (trigger fired, manual `next()`, `complete`, forward `goTo`). The state
   * plugin records progress against this event; analytics treats it as
   * the canonical "step done" signal.
   */
  "step:completed": StepCompletedEvent;
  /**
   * Emitted on every step exit — forward and backward. Superset of
   * `step:completed`. Useful for symmetric cleanup (e.g. clearing the
   * active spotlight) regardless of direction.
   */
  "step:left": StepLeftEvent;
  "target:found": { tourId: string; sectionId: string; stepId: string; element: Element };
  "target:lost": { tourId: string; sectionId: string; stepId: string };
  /**
   * The resolved target is in the DOM but visually covered by another element
   * (a modal/panel on top). Distinct from `target:lost` (target absent). The
   * `occluderId` is an analytics-safe string identifier; `element`/`occluder`
   * are DOM nodes for React consumers only (analytics strips non-serializables).
   */
  "target:occluded": { tourId: string; sectionId: string; stepId: string; element: Element; occluder: Element | null; occluderId: string };
  /** The previously-occluded target is topmost again (recovered or user-resolved). */
  "target:revealed": { tourId: string; sectionId: string; stepId: string; element: Element };
  "navigation:before": NavigationBeforeEvent;
  "navigation:after": NavigationAfterEvent;
  "action:emit": ActionEmitEvent;
}

export type TourBus = Emitter<TourEvents>;

// =============================================================================
// Lifecycle middleware
// =============================================================================

export type LifecycleMiddleware = (ctx: StepContext) => void | Promise<void>;

// =============================================================================
// Preparation hooks
// =============================================================================

/**
 * Result of a preparation hook execution. The `<PreparationRunner />` widget
 * mounts the hook before target resolution; the hook performs whatever
 * app-state mutation the step requires (open a drawer, set pagination, fetch
 * a record) and returns `{ ready: true }` once the relevant DOM has settled.
 * The engine waits for `ready` (or the awaitTarget timeout) before resolving
 * the target.
 */
export interface PreparationResult {
  ready: boolean;
}

/**
 * Preparation callbacks are registered from React components, but the callback
 * itself must not call React hooks. Read React Query caches, Zustand stores,
 * refs, etc. in the outer hook/component and close over stable refs here.
 *
 * Callbacks return a ready signal and may also call `actions.emitAction(...)`
 * to signal completion through the action bus.
 */
export type PreparationHook = (ctx: { stepContext: StepContext; actions: TourActions }) => PreparationResult | Promise<PreparationResult>;

// =============================================================================
// Query-hook target resolvers
// =============================================================================

/**
 * Hook-shaped resolver for `target.kind === "queryHook"`. The engine never
 * calls this as a React hook; consumers register the resolver by reading a
 * live ref or other reactive source from a widget and writing a function that
 * returns the current `Element | null`. The widget is responsible for keeping
 * the resolver up to date — typically by registering inside `useEffect`.
 */
export type QueryHookResolver = () => Element | null;

// =============================================================================
// Occluder surfaces
// =============================================================================

/**
 * A dismissible UI surface (modal / drawer / side panel / popover) the engine
 * can drive closed — and optionally open — during reconcile-on-enter. The
 * engine closes every registered occluder a step does not declare in
 * `StepConfig.surfaces.open`/`keep` before resolving the step's target, so a
 * panel left open by a prior step (or by the user) can't occlude the next
 * step's highlight.
 *
 * Registered from React via `useRegisterOccluder`. The callbacks must not call
 * React hooks — read live state from refs/stores in the owning component and
 * close over stable refs (the same discipline as {@link PreparationHook} /
 * {@link QueryHookResolver}). All callbacks must be idempotent.
 */
export interface OccluderDescriptor {
  /** Stable registry id, e.g. "task-tour.occluder.traceDrawer". */
  id: string;
  /** Pure synchronous read: is the surface currently open? */
  isOpen: () => boolean;
  /**
   * Imperatively close the surface. Must be idempotent (no-op when already
   * closed). May return a promise — URL-driven surfaces should return the
   * router/nuqs update promise so the engine can await the param clear before
   * its route-match check (see the reconcile phase in the engine). The resolved
   * value is ignored.
   */
  close: () => void | Promise<unknown>;
  /**
   * Optional imperative open. `args` is the step-declared open payload
   * (opaque to the engine). Omit for surfaces opened elsewhere (e.g. by a
   * prepare hook that needs async app data). Must be idempotent.
   */
  open?: (args?: unknown) => void | Promise<unknown>;
}

// =============================================================================
// Plugin contract
// =============================================================================

export interface TourEngineStore {
  state: TourState;
  layers: Record<string, number>;
  triggers: Map<string, TriggerFactory>;
  highlights: Map<string, HighlightRenderer>;
  preparations: Map<string, PreparationHook>;
  queryHooks: Map<string, QueryHookResolver>;
  occluders: Map<string, OccluderDescriptor>;
  setState: (next: TourState) => void;
  setLayer: (name: string, z: number) => void;
  registerTrigger: (key: string, factory: TriggerFactory) => void;
  registerHighlight: (key: string, renderer: HighlightRenderer) => void;
  registerPreparation: (key: string, hook: PreparationHook) => void;
  unregisterPreparation: (key: string) => void;
  registerQueryHook: (hookId: string, resolver: QueryHookResolver) => void;
  unregisterQueryHook: (hookId: string) => void;
  registerOccluder: (descriptor: OccluderDescriptor) => void;
  unregisterOccluder: (id: string) => void;
}

export interface TourPluginContext {
  tourId: string;
  store: StoreApi<TourEngineStore>;
  bus: TourBus;
  registerTrigger: (key: string, factory: TriggerFactory) => void;
  registerHighlight: (key: string, renderer: HighlightRenderer) => void;
  registerPreparation: (key: string, hook: PreparationHook) => void;
  registerLayer: (name: string, zIndex: number) => void;
  registerQueryHook: (hookId: string, resolver: QueryHookResolver) => void;
  registerOccluder: (descriptor: OccluderDescriptor) => void;
  use: (middleware: LifecycleMiddleware) => void;
}

export interface TourPlugin {
  name: string;
  install: (ctx: TourPluginContext) => void | (() => void);
}

// =============================================================================
// Trigger contract
// =============================================================================

export interface TriggerAttachContext {
  step: StepConfig;
  stepContext: StepContext;
  targetElement: Element | null;
  bus: TourBus;
  advance: (cause: StepCompletedCause) => void;
  trigger: AdvanceTrigger;
}

export type TriggerFactory = (ctx: TriggerAttachContext) => () => void;

// =============================================================================
// Highlight renderer contract
// =============================================================================

export interface HighlightRenderContext {
  rect: DOMRect | null;
  spec: CustomHighlight;
  backdropColor?: string;
  style?: CSSProperties;
}

export type HighlightRenderer = (ctx: HighlightRenderContext) => ReactNode;
