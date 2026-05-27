import { TASK_TOUR_SECTIONS, type TaskTourItem } from "./data";
import { TASK_TOUR_PULSE_HIGHLIGHT } from "./highlights";
import { tourSelector } from "./selectors";

import type { AdvanceTrigger, RouteSpec, SectionConfig, StepConfig, StepContext, TargetSpec, TourConfig } from "@/features/tour";

const STEP_TIMEOUT_MS = 4000;
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

export interface BuildTourConfigOptions {
  /** Bound at engine build time; the consumer's `skipWhen` predicate consults this map. */
  isEmpty?: (skipWhenEmptyKey: string, ctx: StepContext) => boolean | Promise<boolean>;
}

function buildStep(taskId: string, item: TaskTourItem, opts: BuildTourConfigOptions): StepConfig {
  const route = routeFor(taskId, item);
  const isTracesRouteStep = item.route === "traces";
  const skipWhen = item.skipWhenEmptyKey ? (ctx: StepContext) => Promise.resolve(opts.isEmpty?.(item.skipWhenEmptyKey!, ctx) ?? false) : undefined;
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
    overlay: { blockInteraction: true, onBackdropClick: "none", color: TASK_TOUR_BACKDROP_COLOR },
    ...(route ? { route } : {}),
    ...(item.prepareKey ? { prepare: { key: item.prepareKey } } : {}),
    ...(skipWhen ? { skipWhen } : {}),
    awaitTarget: { timeoutMs: isTracesRouteStep ? TRACES_STEP_TIMEOUT_MS : STEP_TIMEOUT_MS },
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
