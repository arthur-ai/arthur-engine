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

export interface StepConfig {
  id: string;
  target: TargetSpec;
  content: ReactNode | ((ctx: StepRenderContext) => ReactNode);
  placement?: Placement;
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
export type StepLifecycleEvent = StepContext;

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
// Plugin contract
// =============================================================================

export interface TourEngineStore {
  state: TourState;
  layers: Record<string, number>;
  triggers: Map<string, TriggerFactory>;
  highlights: Map<string, HighlightRenderer>;
  preparations: Map<string, PreparationHook>;
  queryHooks: Map<string, QueryHookResolver>;
  setState: (next: TourState) => void;
  setLayer: (name: string, z: number) => void;
  registerTrigger: (key: string, factory: TriggerFactory) => void;
  registerHighlight: (key: string, renderer: HighlightRenderer) => void;
  registerPreparation: (key: string, hook: PreparationHook) => void;
  unregisterPreparation: (key: string) => void;
  registerQueryHook: (hookId: string, resolver: QueryHookResolver) => void;
  unregisterQueryHook: (hookId: string) => void;
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
