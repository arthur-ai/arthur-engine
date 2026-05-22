import { TASK_TOUR_SECTIONS, type TaskTourItem } from "./data";
import { tourSelector } from "./selectors";

import type { AdvanceTrigger, RouteSpec, SectionConfig, StepConfig, TourConfig } from "@/features/tour";

const STUB_STEP_ID = "__placeholder";
const STEP_TIMEOUT_MS = 4000;

/**
 * Sentinel selector used by stub / intro-only sections. The placeholder step
 * exists only to satisfy the engine's "every section must have at least one
 * step" contract; `ChecklistTour.tsx` watches for the placeholder and calls
 * `engine.next()` immediately so the user never sees it.
 */
const STUB_TARGET = "body";

function routeFor(taskId: string, item: TaskTourItem): RouteSpec | undefined {
  if (!item.route) return undefined;
  return {
    path: "/tasks/:taskId/:page",
    params: { taskId, page: item.route },
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
    // Brand-coloured pulse is painted by `PulsingRing` — keep the library
    // spotlight non-pulsing.
    highlight: { shape: "box", padding: 6, radius: 10, pulse: false },
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
      secondaryActionLabel: "Skip this section",
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

export function getStubAdvanceEventName(sectionId: string): string {
  return `task-tour:stub:${sectionId}`;
}
