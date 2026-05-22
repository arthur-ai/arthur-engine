import type { Placement } from "@floating-ui/react";
import type { Emitter, EventType } from "mitt";
import type { CSSProperties, ReactNode, RefObject } from "react";

// =============================================================================
// Target resolution
// =============================================================================

export type TargetSpec =
  | { kind: "selector"; selector: string }
  | { kind: "element"; resolve: () => Element | null }
  | { kind: "ref"; ref: RefObject<Element | null> };

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
// Advance triggers (when does a step move forward?)
// =============================================================================

export type AdvanceTrigger =
  | { type: "manual" }
  | { type: "click"; selector?: string }
  | { type: "visible"; threshold?: number; rootMargin?: string }
  | { type: "event"; name: string }
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

/**
 * Custom highlight shape rendered via a plugin-registered renderer. The `key`
 * must match a name passed to `registerHighlight(...)` in a `TourPlugin`'s
 * install hook; if no renderer is registered, the built-in `Spotlight` falls
 * back to a box cutout.
 *
 * `padding` is exposed at the top level so primitives like `BackdropBlocker`
 * can size the interactive cutout to match the visual one without unpacking
 * `options`. Renderer-specific config goes into `options`.
 */
export type CustomHighlight = {
  shape: "custom";
  key: string;
  padding?: number;
  options?: unknown;
};

export type HighlightSpec = BoxHighlight | CircleHighlight | NoHighlight | CustomHighlight;

// =============================================================================
// Overlay (focus mode)
// =============================================================================

/**
 * Optional configuration for the tour overlay/backdrop. By default the spotlight
 * is purely visual and pointer events fall through, so the user can still
 * interact with anything on the page. When `blockInteraction` is enabled, an
 * interactive backdrop is rendered around the spotlight cutout so the user can
 * only interact with the highlighted target (or the tour popover) — useful for
 * "really focus on one part of the app" walkthroughs.
 */
export interface OverlayConfig {
  /**
   * When true, an interactive backdrop blocks pointer events on the page
   * outside the spotlight cutout. The cutout itself stays clickable so the
   * user can still interact with the highlighted target. When false (the
   * default), the overlay is purely visual.
   */
  blockInteraction?: boolean;
  /**
   * Action to perform when the user clicks the backdrop (the area outside the
   * spotlight cutout and the popover). Only honored when `blockInteraction` is
   * true. Default: `"none"`.
   *
   * - `"none"`: absorb the click and do nothing (user stays on the step).
   * - `"next"`: advance to the next step.
   * - `"skip"`: skip the entire tour.
   * - `"dismiss"`: pause the tour and emit `tour:dismiss`.
   */
  onBackdropClick?: "none" | "next" | "skip" | "dismiss";
  /**
   * Override the backdrop color (CSS color string, typically rgba). Forwarded
   * to the visual `Spotlight` so the visual and interactive layers stay
   * consistent.
   */
  color?: string;
}

// =============================================================================
// Section / step / tour configuration
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

export interface StepConfig {
  id: string;
  target: TargetSpec;
  content: ReactNode | ((ctx: StepRenderContext) => ReactNode);
  placement?: Placement;
  highlight?: HighlightSpec;
  /**
   * Per-step overlay/backdrop configuration. When omitted, the overlay is
   * purely visual (the spotlight dims the page but pointer events fall
   * through). Set `blockInteraction: true` to focus the user on the
   * highlighted target.
   */
  overlay?: OverlayConfig;
  advanceOn?: AdvanceTrigger | AdvanceTrigger[];
  awaitTarget?: { timeoutMs?: number };
  route?: string | RouteSpec;
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
  steps: StepConfig[];
  onEnter?: (ctx: { tourId: string; sectionId: string }) => void | Promise<void>;
  onExit?: (ctx: { tourId: string; sectionId: string }) => void | Promise<void>;
}

export interface TourConfig {
  id: string;
  sections: SectionConfig[];
}

// =============================================================================
// State machine
// =============================================================================

export type TourState =
  | { status: "idle" }
  | {
      status: "running";
      sectionId: string;
      stepId: string;
      sectionIndex: number;
      stepIndex: number;
      globalStepIndex: number;
      totalSteps: number;
      introductionPending: boolean;
    }
  | { status: "paused"; sectionId: string; stepId: string }
  | { status: "completed" }
  | { status: "skipped"; reason: SkipReason };

export type SkipReason = "user" | "section" | "programmatic";

// =============================================================================
// Public actions
// =============================================================================

export interface TourActions {
  start: (options?: { sectionId?: string; stepId?: string }) => void;
  next: () => void;
  prev: () => void;
  goTo: (target: { sectionId: string; stepId?: string }) => void;
  skipSection: () => void;
  skip: (reason?: SkipReason) => void;
  pause: () => void;
  resume: () => void;
  /**
   * Pause the tour and emit `tour:dismiss`. Use this for "user closed the
   * panel" — the engine retains its position so a subsequent `resume()` (or
   * `start()` from a fresh session) picks up where the user left off, and
   * persistence-aware plugins can mark the tour as dismissed.
   */
  dismiss: () => void;
  acknowledgeIntroduction: () => void;
}

// =============================================================================
// Event bus
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

export interface StepAdvanceEvent extends StepContext {
  triggerType: AdvanceTrigger["type"];
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

export interface TourEvents extends Record<EventType, unknown> {
  "tour:start": { tourId: string };
  "tour:end": { tourId: string; reason: "completed" | "skipped" };
  "tour:pause": { tourId: string };
  "tour:resume": { tourId: string };
  "tour:dismiss": { tourId: string };
  "section:enter": SectionEnterEvent;
  "section:exit": SectionExitEvent;
  "section:skip": SectionSkipEvent;
  "section:introduction:show": { tourId: string; sectionId: string };
  "section:introduction:acknowledge": { tourId: string; sectionId: string };
  "step:before-enter": StepLifecycleEvent;
  "step:enter": StepEnterEvent;
  "step:exit": StepLifecycleEvent;
  "step:advance": StepAdvanceEvent;
  "target:found": { stepId: string; element: Element };
  "target:lost": { stepId: string };
  "navigation:before": NavigationBeforeEvent;
  "navigation:after": NavigationAfterEvent;
}

export type TourBus = Emitter<TourEvents>;

// =============================================================================
// Middleware (for async side-effects in the enter pipeline)
// =============================================================================

export type LifecycleMiddleware = (ctx: StepContext) => void | Promise<void>;

// =============================================================================
// Plugin contract
// =============================================================================

export interface TourPluginContext {
  tourId: string;
  bus: TourBus;
  registerTrigger: (key: string, factory: TriggerFactory) => void;
  registerHighlight: (shape: string, renderer: HighlightRenderer) => void;
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
  advance: (triggerType: AdvanceTrigger["type"]) => void;
  trigger: AdvanceTrigger;
}

export type TriggerFactory = (ctx: TriggerAttachContext) => () => void;

// =============================================================================
// Highlight renderer contract (for plugin-supplied custom shapes)
// =============================================================================

/**
 * Context passed to a registered highlight renderer. `rect` may be `null`
 * when the active step's target hasn't resolved yet — renderers that depend
 * on a rect should bail out in that case (returning `null`) rather than
 * paint a fallback. `backdropColor` and `style` are forwarded from the
 * `Spotlight` primitive so renderers can produce visuals consistent with the
 * surrounding overlay configuration without the caller wiring those props
 * twice.
 */
export interface HighlightRenderContext {
  rect: DOMRect | null;
  spec: CustomHighlight;
  backdropColor?: string;
  style?: CSSProperties;
}

export type HighlightRenderer = (ctx: HighlightRenderContext) => ReactNode;
