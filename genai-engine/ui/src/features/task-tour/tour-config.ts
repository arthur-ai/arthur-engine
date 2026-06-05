import { TASK_TOUR_PREPARATIONS } from "./content/wiring";
import { TASK_TOUR_SECTIONS, type TaskTourItem } from "./data";
import { TASK_TOUR_PULSE_HIGHLIGHT } from "./highlights";
import { TASK_TOUR_OCCLUDERS } from "./occluders";
import { tourSelector } from "./selectors";

import type { AdvanceTrigger, RouteSpec, SectionConfig, StepConfig, StepContext, TargetSpec, TourConfig } from "@/features/tour";

const STEP_TIMEOUT_MS = 4000;
const PROMPT_DETAIL_STEP_TIMEOUT_MS = 10_000;
/**
 * Trace steps mount lazily (route + drawer chunk + suspense query). The
 * `prepare` hook for trace steps opens the drawer and waits for the table to
 * settle, but the engine still falls back to async-target resolution after the
 * hook returns, so we keep a long upper bound.
 */
const TRACES_STEP_TIMEOUT_MS = 20_000;
const TASK_TOUR_BACKDROP_COLOR = "rgba(15, 23, 42, 0.68)";

/** Build a `RouteSpec` for `/tasks/:taskId/<sub-route>` from a tour item. */
function routeFor(taskId: string, item: TaskTourItem): RouteSpec | undefined {
  if (!item.route) return undefined;
  return {
    path: `/tasks/:taskId/${item.route}`,
    params: { taskId },
    search: item.search,
  };
}

function advanceFor(item: TaskTourItem): AdvanceTrigger[] {
  if (item.advance === "manual") return [{ type: "manual" }];
  const actionTrigger: AdvanceTrigger = { type: "action", name: item.actionName };
  if (item.advance === "action-only") return [actionTrigger];
  return [{ type: "click" }, actionTrigger];
}

function targetFor(item: TaskTourItem): TargetSpec {
  if (item.targetHookId) {
    return { kind: "queryHook", hookId: item.targetHookId };
  }
  return { kind: "selector", selector: tourSelector(item.targetId) };
}

/**
 * Declarative occluder reconcile config for a step. Steps that open the trace
 * drawer (every `prepareKey: traceOpened` beat — the `DRAWER_STEPS` set) keep
 * it open so reconcile doesn't fight the prep hook; any other surface a step
 * needs open is listed explicitly via `surfacesOpen`. All unlisted registered
 * occluders are closed on entry.
 */
function surfacesFor(item: TaskTourItem): StepConfig["surfaces"] | undefined {
  const open: Array<{ id: string; args?: unknown }> = [];
  if (item.prepareKey === TASK_TOUR_PREPARATIONS.traceOpened) {
    open.push({ id: TASK_TOUR_OCCLUDERS.traceDrawer });
  }
  if (item.surfacesOpen) open.push(...item.surfacesOpen);
  const keep = item.surfacesKeep;
  if (open.length === 0 && (!keep || keep.length === 0)) return undefined;
  return { ...(open.length ? { open } : {}), ...(keep && keep.length ? { keep } : {}) };
}

export interface BuildTourConfigOptions {
  /** Bound at engine build time; the consumer's `skipWhen` predicate consults this map. */
  isEmpty?: (skipWhenEmptyKey: string, ctx: StepContext) => boolean | Promise<boolean>;
}

function buildStep(taskId: string, item: TaskTourItem, opts: BuildTourConfigOptions): StepConfig {
  const route = routeFor(taskId, item);
  const isTracesRouteStep = item.route === "traces";
  const isPromptDetailStep = item.targetHookId === "task-tour.promptOpenInPlayground";
  // Steps whose prep navigates to a dynamic detail route need a longer target
  // wait — navigation + detail-page data load takes more than the default.
  const isDetailPrepStep =
    item.prepareKey === TASK_TOUR_PREPARATIONS.evaluatorDetailOpened ||
    item.prepareKey === TASK_TOUR_PREPARATIONS.datasetDetailOpened ||
    item.prepareKey === TASK_TOUR_PREPARATIONS.promptDetailOpened ||
    item.prepareKey === TASK_TOUR_PREPARATIONS.playgroundOpened;
  const skipWhen = item.skipWhenEmptyKey ? (ctx: StepContext) => Promise.resolve(opts.isEmpty?.(item.skipWhenEmptyKey!, ctx) ?? false) : undefined;
  const surfaces = surfacesFor(item);
  return {
    id: item.id,
    target: targetFor(item),
    content: item.instructions,
    highlight: {
      shape: "custom",
      key: TASK_TOUR_PULSE_HIGHLIGHT,
      padding: 6,
      options: { radius: 10 },
    },
    overlay: { blockInteraction: item.blockInteraction ?? true, onBackdropClick: "none", color: TASK_TOUR_BACKDROP_COLOR },
    ...(route ? { route } : {}),
    ...(item.popover ? { popover: item.popover } : {}),
    ...(item.formPrefill ? { formPrefill: item.formPrefill } : {}),
    ...(item.prepareKey ? { prepare: { key: item.prepareKey } } : {}),
    ...(surfaces ? { surfaces } : {}),
    ...(skipWhen ? { skipWhen } : {}),
    awaitTarget: {
      timeoutMs: isTracesRouteStep
        ? TRACES_STEP_TIMEOUT_MS
        : isPromptDetailStep || isDetailPrepStep
          ? PROMPT_DETAIL_STEP_TIMEOUT_MS
          : STEP_TIMEOUT_MS,
    },
    advanceOn: advanceFor(item),
  };
}

/**
 * Build the engine `TourConfig` for the task tour. v1 supports intro-only
 * sections natively (the engine handles `acknowledgeIntroduction()` →
 * advance-to-next-section when `steps.length === 0`), so the v0 stub-step
 * placeholder is gone.
 */
export function buildTourConfig(taskId: string, opts: BuildTourConfigOptions = {}): TourConfig {
  const sections: SectionConfig[] = TASK_TOUR_SECTIONS.map((section) => ({
    id: section.id,
    title: section.title,
    introduction: {
      title: section.intro.heading,
      description: section.intro.body,
      primaryActionLabel: section.intro.cta,
    },
    skipable: true,
    steps: section.items.map((item) => buildStep(taskId, item, opts)),
  }));

  return {
    id: "task-tour-evals-101",
    sectionCompletion: "pause",
    sections,
  };
}

/**
 * Human-readable label for a task-tour step, keyed by engine section/step IDs.
 * Intro-only sections fall back to the section intro heading; real steps use
 * the item title from the author-friendly section list.
 */
export function getTaskTourStepLabel(sectionId: string, stepId: string | undefined): string {
  const section = TASK_TOUR_SECTIONS.find((candidate) => candidate.id === sectionId);
  if (!section) return "Resume tour";
  if (!stepId || section.items.length === 0) return section.intro.heading;
  const item = section.items.find((candidate) => candidate.id === stepId);
  return item?.title ?? section.title;
}
