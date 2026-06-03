import { TASK_TOUR_SECTIONS, type TaskTourSection } from "./data";

/**
 * Single source of truth for the task-tour progress-key convention. The engine's
 * `createTourStatePlugin` records completion under these keys (the step key is
 * passed to it as `getKey`), and the checklist UI reads them back here — so the
 * persisted shape and the UI can never silently drift apart.
 *
 * - Step keys: `${sectionId}.${stepId}` ({@link itemKey}).
 * - Intro-acknowledged keys: `${sectionId}.__intro` ({@link introKey}) — mirrors
 *   the engine plugin's documented `__intro` convention for intro acks.
 */
export const INTRO_KEY_SUFFIX = "__intro";

export function itemKey(sectionId: string, itemId: string): string {
  return `${sectionId}.${itemId}`;
}

export function introKey(sectionId: string): string {
  return `${sectionId}.${INTRO_KEY_SUFFIX}`;
}

/**
 * A section is complete when every step key is recorded — or, for an intro-only
 * section (no steps), when its intro key is recorded.
 */
export function isSectionComplete(section: TaskTourSection, completed: ReadonlySet<string>): boolean {
  if (section.items.length === 0) return completed.has(introKey(section.id));
  return section.items.every((item) => completed.has(itemKey(section.id, item.id)));
}

/**
 * Total completion units across the whole tour: one intro per section plus one
 * per step. The engine emits `section:intro:acknowledge` for every section (so a
 * `__intro` key lands for each) and one `step:completed` per step — so this is
 * exactly the size the `completed` set reaches at 100%, keeping a progress ratio
 * built from it within [0, 1].
 */
export const TASK_TOUR_TOTAL_UNITS = TASK_TOUR_SECTIONS.reduce((sum, section) => sum + section.items.length + 1, 0);
