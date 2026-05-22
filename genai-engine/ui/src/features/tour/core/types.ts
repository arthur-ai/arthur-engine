import type { Placement } from "@floating-ui/react";
import type { Emitter, EventType } from "mitt";
import type { ReactNode, RefObject } from "react";

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

export type CustomHighlight = { shape: "custom"; key: string; options?: unknown };

export type HighlightSpec = BoxHighlight | CircleHighlight | NoHighlight | CustomHighlight;

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

export interface HighlightRenderContext {
  rect: DOMRect;
  spec: HighlightSpec;
}

export type HighlightRenderer = (ctx: HighlightRenderContext) => ReactNode;
