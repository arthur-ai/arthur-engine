import type { ReactNode } from "react";

import { TASK_TOUR_META, TASK_TOUR_SECTIONS } from "./content/loader";
import type { StepWiring, TaskSubRoute } from "./content/wiring";

export type { TaskSubRoute } from "./content/wiring";

export interface TaskTourSearchParams {
  /** Optional query params appended to the route (`?section=evaluators` etc.). */
  search?: Record<string, string>;
}

/**
 * One step inside a section. Engineering wiring (`targetId`, `route`,
 * `eventName`, `advance`, `search`) is sourced from
 * [content/wiring.ts](./content/wiring.ts). Marketing-controlled fields
 * (`title`, `instructions`) come from per-section markdown files under
 * [content/](./content/).
 *
 * - `instructions` is rendered prose: typically `<Markdown>...</Markdown>`
 *   built from the matching `## step: <id>` body block, but any `ReactNode`
 *   works for consumers that compose their own copy.
 */
export interface TaskTourItem {
  id: string;
  title: string;
  instructions: ReactNode;
  targetId: StepWiring["targetId"];
  /** Optional queryHook ID — when present, supersedes the static selector. */
  targetHookId?: string;
  route?: TaskSubRoute;
  search?: Record<string, string>;
  actionName: string;
  advance?: StepWiring["advance"];
  prepareKey?: string;
  skipWhenEmptyKey?: string;
  popover?: StepWiring["popover"];
  formPrefill?: StepWiring["formPrefill"];
  /** Overrides the default click-blocking backdrop; defaults to `true`. */
  blockInteraction?: StepWiring["blockInteraction"];
}

/**
 * Optional hero illustration shown above the section intro body. Resolved at
 * load time against [content/assets/](./content/assets/); an unresolved path
 * throws during section parsing so a broken hero never reaches production.
 */
export interface TaskTourHero {
  src: string;
  alt: string;
  width?: number;
}

export interface TaskTourSection {
  id: string;
  title: string;
  kicker: string;
  intro: {
    heading: string;
    /** Long-form prose, rendered via `<Markdown>` at load time. */
    body: ReactNode;
    /** If true, the section intro renders the ADLC flywheel hero diagram. */
    showFlywheel?: boolean;
    /** Optional hero illustration above the intro body. */
    hero?: TaskTourHero;
    scenario?: {
      label: string;
      /** Long-form scenario text, rendered via `<Markdown>` at load time. */
      text: ReactNode;
    };
    cta: string;
  };
  /**
   * The section's steps. v1 supports `items.length === 0` natively — an
   * intro-only section advances straight from `intro:acknowledge` to the
   * next section without the v0 stub-step placeholder.
   */
  items: TaskTourItem[];
}

export const TASK_TOUR_TITLE = TASK_TOUR_META.title;
export const TASK_TOUR_SHORT_NAME = TASK_TOUR_META.shortName;
export const TASK_TOUR_SUBTITLE = TASK_TOUR_META.subtitle;

/**
 * Author-friendly representation of the tour. Each section maps 1:1 to an
 * engine `SectionConfig`; sections with `items.length === 0` collapse to a
 * stub step.
 *
 * The tour is anchored on a single worked example: an agent that answers
 * questions from Wikipedia but never cites its source, so the Source
 * Attribution Eval fails on every response. Every section's copy, scenario,
 * and step instructions reinforce that scenario — the user diagnoses the
 * citation failures with traces + continuous evals, captures them in a
 * dataset, fixes the prompt so the agent attributes its answers in the prompt
 * playground, and ships the winning version.
 */
export { TASK_TOUR_SECTIONS } from "./content/loader";

export function findSection(sectionId: string): TaskTourSection | undefined {
  return TASK_TOUR_SECTIONS.find((s) => s.id === sectionId);
}

export function findItem(sectionId: string, itemId: string): TaskTourItem | undefined {
  return findSection(sectionId)?.items.find((i) => i.id === itemId);
}
