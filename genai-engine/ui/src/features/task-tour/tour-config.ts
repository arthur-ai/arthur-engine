import { TASK_TOUR_SECTIONS, type TaskTourItem } from "./data";
import { TASK_TOUR_PULSE_HIGHLIGHT } from "./highlights";
import { tourSelector } from "./selectors";

import type { AdvanceTrigger, RouteSpec, SectionConfig, StepConfig, TourConfig } from "@/features/tour";

const STUB_STEP_ID = "__placeholder";
const STEP_TIMEOUT_MS = 4000;
/**
 * Backdrop tint used by the focus-mode overlay around every spotlighted step.
 * Declared on each `StepConfig.overlay.color` so the engine config is the
 * source of truth — `ChecklistTour` keeps an identical hardcoded fallback for
 * defensive defaulting only.
 */
const TASK_TOUR_BACKDROP_COLOR = "rgba(15, 23, 42, 0.68)";

/**
 * Sentinel selector used by stub / intro-only sections. The placeholder step
 * exists only to satisfy the engine's "every section must have at least one
 * step" contract; `ChecklistTour.tsx` watches for the placeholder and calls
 * `actions.next()` immediately so the user never sees it.
 */
const STUB_TARGET = "body";

/**
 * Build a `RouteSpec` for `/tasks/:taskId/<sub-route>` from a tour item.
 * The sub-route is interpolated into the path string directly (not as a
 * `:param`) so multi-segment routes like `playgrounds/prompts` keep their
 * `/` separators — encoding via `params` would percent-encode the slash.
 */
function routeFor(taskId: string, item: TaskTourItem): RouteSpec | undefined {
  if (!item.route) return undefined;
  return {
    path: `/tasks/:taskId/${item.route}`,
    params: { taskId },
    search: item.search,
  };
}

function advanceFor(item: TaskTourItem): AdvanceTrigger[] {
  const eventTrigger: AdvanceTrigger = { type: "event", name: item.eventName };
  if (item.advance === "event-only") return [eventTrigger];
  // Default: click on the spotlighted target OR the panel's "Mark step
  // complete" event — whichever fires first advances.
  return [{ type: "click" }, eventTrigger];
}

function buildStep(taskId: string, item: TaskTourItem): StepConfig {
  const route = routeFor(taskId, item);
  return {
    id: item.id,
    target: { kind: "selector", selector: tourSelector(item.targetId) },
    content: item.instructions,
    // Brand-coloured cutout + pulse — handed off to the engine's highlight
    // registry so the spotlight composition lives behind the same plugin
    // contract as triggers and persistence (registered by
    // `createTaskTourHighlightsPlugin`). `padding` is duplicated at the top
    // level so `BackdropBlocker` can size the interactive cutout to match.
    highlight: {
      shape: "custom",
      key: TASK_TOUR_PULSE_HIGHLIGHT,
      padding: 6,
      options: { radius: 10 },
    },
    // Block interaction with everything outside the spotlight so the user can
    // only engage with the highlighted target (or the floating checklist
    // panel, which sits above the blocker via z-index). Backdrop clicks are
    // intentionally a no-op — the panel exposes explicit Skip / Close /
    // Dismiss controls so a stray click on the dim can't end the tour.
    overlay: { blockInteraction: true, onBackdropClick: "none", color: TASK_TOUR_BACKDROP_COLOR },
    ...(route ? { route } : {}),
    awaitTarget: { timeoutMs: STEP_TIMEOUT_MS },
    advanceOn: advanceFor(item),
  };
}

function buildStubStep(sectionId: string): StepConfig {
  return {
    id: STUB_STEP_ID,
    target: { kind: "selector", selector: STUB_TARGET },
    content: "",
    highlight: { shape: "none" },
    advanceOn: { type: "event", name: `task-tour:stub:${sectionId}` },
  };
}

/**
 * Builds the engine `TourConfig` from the author-friendly section list,
 * resolving every section/step against the supplied `taskId` so navigation
 * routes through `/tasks/:taskId/...` correctly.
 */
export function buildTourConfig(taskId: string): TourConfig {
  const sections: SectionConfig[] = TASK_TOUR_SECTIONS.map((section) => ({
    id: section.id,
    title: section.title,
    introduction: {
      title: section.intro.heading,
      description: section.intro.body,
      primaryActionLabel: section.intro.cta,
    },
    skipable: true,
    steps: section.items.length === 0 ? [buildStubStep(section.id)] : section.items.map((item) => buildStep(taskId, item)),
  }));

  return {
    id: "task-tour-evals-101",
    sections,
  };
}

export function isStubStep(stepId: string): boolean {
  return stepId === STUB_STEP_ID;
}

/**
 * Human-readable label for a task-tour step, keyed by engine section/step IDs.
 * Stub steps fall back to the section intro heading; real steps use the item
 * title from the author-friendly section list.
 */
export function getTaskTourStepLabel(sectionId: string, stepId: string): string {
  const section = TASK_TOUR_SECTIONS.find((candidate) => candidate.id === sectionId);
  if (!section) {
    return "Resume tour";
  }

  if (isStubStep(stepId) || section.items.length === 0) {
    return section.intro.heading;
  }

  const item = section.items.find((candidate) => candidate.id === stepId);
  return item?.title ?? section.title;
}

export function getStubAdvanceEventName(sectionId: string): string {
  return `task-tour:stub:${sectionId}`;
}
