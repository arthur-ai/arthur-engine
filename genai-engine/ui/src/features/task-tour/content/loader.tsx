import matter from "gray-matter";
import type { ReactNode } from "react";

import { Markdown } from "../components/Markdown";
import type { TaskTourItem, TaskTourSection } from "../data";

import { resolveAssetSrc } from "./assetMap";
import { MetaFrontmatterSchema, SectionFrontmatterSchema, type MetaFrontmatter, type SectionFrontmatter } from "./schema";
import { TASK_TOUR_WIRING } from "./wiring";

/**
 * Raw markdown sources for every section file, keyed by Vite-relative path
 * (e.g. `./00-intro.md`). The numeric prefix on each filename encodes tour
 * order; `id` in the frontmatter is the contract used everywhere downstream.
 */
const rawSectionFiles = import.meta.glob("./*.md", {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

/** Pattern for a top-level body heading inside a section file. */
const HEADING_PATTERN = /^##\s+(.+?)\s*$/;

/**
 * A failure during load surfaces as a clear, prefixed error so the Vite
 * dev-server overlay (or production logs) points directly at the file that
 * needs fixing.
 */
function fail(file: string, message: string): never {
  throw new Error(`[task-tour content] ${file}: ${message}`);
}

/**
 * Split a markdown body into a record keyed by `## <name>` heading.
 *
 * Heading names that match `step: <id>` are split into a `steps[id]` map so
 * the loader can cross-check them against `frontmatter.steps` and wiring.
 *
 * Throws on duplicate headings so a copy-paste typo (two `## intro` blocks or
 * the same `## step: open-evaluate` twice) surfaces immediately instead of
 * silently overwriting earlier content.
 */
function splitBody(file: string, body: string): { intro: string; scenario?: string; steps: Record<string, string> } {
  const lines = body.split(/\r?\n/);
  let current: string | null = null;
  const blocks: Record<string, string[]> = {};
  const seen = new Set<string>();

  for (const line of lines) {
    const match = HEADING_PATTERN.exec(line);
    if (match) {
      current = match[1].trim();
      if (seen.has(current)) {
        fail(file, `duplicate "## ${current}" heading — each heading must appear at most once per file`);
      }
      seen.add(current);
      blocks[current] = [];
      continue;
    }
    if (current) {
      blocks[current].push(line);
    }
  }

  const stepBlocks: Record<string, string> = {};
  let intro = "";
  let scenario: string | undefined;
  for (const [name, contentLines] of Object.entries(blocks)) {
    const text = contentLines.join("\n").trim();
    if (name === "intro") intro = text;
    else if (name === "scenario") scenario = text;
    else if (name.startsWith("step:")) stepBlocks[name.slice("step:".length).trim()] = text;
  }

  return { intro, scenario, steps: stepBlocks };
}

/**
 * Resolve an `intro.hero.src` against the asset map. Throws on miss because a
 * broken hero is a publishing bug we want to catch immediately, not silently
 * drop in production.
 */
function resolveHeroOrThrow(file: string, src: string): string {
  const resolved = resolveAssetSrc(src);
  if (!resolved) {
    fail(file, `intro.hero.src "${src}" does not resolve to a file in content/assets/`);
  }
  return resolved;
}

/**
 * Validate that the set of step ids in frontmatter, body headings, and wiring
 * are all identical (or all empty, for stub sections). Surfaces a precise
 * mismatch message so authors can fix the source of truth, not guess.
 */
function checkStepConsistency(file: string, sectionId: string, frontmatterStepIds: readonly string[], bodyStepIds: readonly string[]): void {
  const wiring = TASK_TOUR_WIRING[sectionId];
  if (!wiring) {
    fail(file, `section id "${sectionId}" has no entry in content/wiring.ts`);
  }

  const wiringStepIds = Object.keys(wiring.steps);

  const sameSet = (a: readonly string[], b: readonly string[]): boolean => a.length === b.length && a.every((id) => b.includes(id));

  if (!sameSet(frontmatterStepIds, bodyStepIds)) {
    fail(file, `frontmatter steps [${frontmatterStepIds.join(", ")}] don't match "## step: <id>" headings [${bodyStepIds.join(", ")}]`);
  }

  if (!sameSet(frontmatterStepIds, wiringStepIds)) {
    fail(file, `frontmatter steps [${frontmatterStepIds.join(", ")}] don't match wiring.ts steps [${wiringStepIds.join(", ")}]`);
  }
}

/**
 * Build the engine-ready `TaskTourItem` list for a section by zipping the
 * frontmatter step entries (which define order + display title) with the
 * wiring map (which holds the targetId / route / eventName / advance) and the
 * body's per-step prose (pre-rendered to ReactNode).
 */
function buildItems(sectionId: string, frontmatter: SectionFrontmatter, bodyStepText: Record<string, string>): TaskTourItem[] {
  const wiring = TASK_TOUR_WIRING[sectionId];
  return frontmatter.steps.map((step) => {
    const wired = wiring.steps[step.id];
    return {
      id: step.id,
      title: step.title,
      instructions: <Markdown variant="caption">{bodyStepText[step.id] ?? ""}</Markdown>,
      targetId: wired.targetId,
      targetHookId: wired.targetHookId,
      actionName: wired.actionName,
      route: wired.route,
      search: wired.search,
      advance: wired.advance,
      prepareKey: wired.prepareKey,
      skipWhenEmptyKey: wired.skipWhenEmptyKey,
      popover: wired.popover,
      formPrefill: wired.formPrefill,
      blockInteraction: wired.blockInteraction,
    };
  });
}

/**
 * Wrap `gray-matter` so YAML parse failures surface as our prefixed error
 * pointing at the offending file, rather than the library's stack trace.
 */
function parseFrontmatter(file: string, raw: string): ReturnType<typeof matter> {
  try {
    return matter(raw);
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    fail(file, `failed to parse frontmatter (check YAML indentation and quoting): ${detail}`);
  }
}

/**
 * Parse a single section markdown file into the runtime `TaskTourSection`
 * shape. Validates frontmatter, splits the body, and merges with wiring.
 */
function parseSection(file: string, raw: string): TaskTourSection {
  const parsed = parseFrontmatter(file, raw);
  const frontmatterResult = SectionFrontmatterSchema.safeParse(parsed.data);
  if (!frontmatterResult.success) {
    const issues = frontmatterResult.error.issues.map((issue) => `  - ${issue.path.join(".") || "(root)"}: ${issue.message}`).join("\n");
    fail(file, `frontmatter failed validation:\n${issues}`);
  }
  const frontmatter = frontmatterResult.data;

  const body = splitBody(file, parsed.content);

  const wiring = TASK_TOUR_WIRING[frontmatter.id];
  if (!wiring) {
    fail(file, `section id "${frontmatter.id}" has no entry in content/wiring.ts`);
  }
  const isIntroOnly = Object.keys(wiring.steps).length === 0;

  if (!isIntroOnly && body.intro.length === 0) {
    fail(file, `section with steps must contain a "## intro" block`);
  }
  if (frontmatter.intro.scenario && !body.scenario) {
    fail(file, `intro.scenario.label is set but body has no "## scenario" block`);
  }

  checkStepConsistency(
    file,
    frontmatter.id,
    frontmatter.steps.map((s) => s.id),
    Object.keys(body.steps)
  );

  const heroSrc = frontmatter.intro.hero ? resolveHeroOrThrow(file, frontmatter.intro.hero.src) : undefined;

  const introBodyNode: ReactNode = body.intro ? <Markdown variant="body2">{body.intro}</Markdown> : null;
  const scenarioNode: ReactNode | undefined = body.scenario ? <Markdown variant="body2">{body.scenario}</Markdown> : undefined;

  return {
    id: frontmatter.id,
    title: frontmatter.title,
    kicker: frontmatter.kicker,
    intro: {
      heading: frontmatter.intro.heading,
      body: introBodyNode,
      cta: frontmatter.intro.cta,
      showFlywheel: frontmatter.intro.showFlywheel,
      hero:
        frontmatter.intro.hero && heroSrc
          ? {
              src: heroSrc,
              alt: frontmatter.intro.hero.alt,
              width: frontmatter.intro.hero.width,
            }
          : undefined,
      scenario:
        frontmatter.intro.scenario && scenarioNode
          ? {
              label: frontmatter.intro.scenario.label,
              text: scenarioNode,
            }
          : undefined,
    },
    items: isIntroOnly ? [] : buildItems(frontmatter.id, frontmatter, body.steps),
  };
}

/**
 * Load and parse `_meta.md`. The body is treated as comments — only the
 * frontmatter is consumed.
 */
function loadMeta(): MetaFrontmatter {
  const file = "./_meta.md";
  const raw = rawSectionFiles[file];
  if (!raw) {
    throw new Error("[task-tour content] _meta.md is missing");
  }
  const parsed = parseFrontmatter(file, raw);
  const result = MetaFrontmatterSchema.safeParse(parsed.data);
  if (!result.success) {
    const issues = result.error.issues.map((issue) => `  - ${issue.path.join(".") || "(root)"}: ${issue.message}`).join("\n");
    fail(file, `frontmatter failed validation:\n${issues}`);
  }
  return result.data;
}

/** Files in `content/` that are not tour sections and should be skipped by the loader. */
const NON_SECTION_FILES: ReadonlySet<string> = new Set(["_meta.md", "README.md"]);

function basename(path: string): string {
  const idx = path.lastIndexOf("/");
  return idx >= 0 ? path.slice(idx + 1) : path;
}

/**
 * Load every section markdown file (excluding `_meta.md` / `README.md`),
 * sorted by file name so the numeric prefix encodes tour order. Cross-checks
 * every section against `wiring.ts` to ensure marketing and engineering
 * haven't drifted.
 */
function loadSections(): TaskTourSection[] {
  const entries = Object.entries(rawSectionFiles)
    .filter(([file]) => !NON_SECTION_FILES.has(basename(file)))
    .sort(([a], [b]) => a.localeCompare(b));

  if (entries.length === 0) {
    throw new Error("[task-tour content] no section markdown files found under content/");
  }

  return entries.map(([file, raw]) => parseSection(file, raw));
}

/** Top-level tour labels (title, short name, subtitle). */
export const TASK_TOUR_META: MetaFrontmatter = loadMeta();

/** Ordered list of tour sections, ready to be consumed by `tour-config.ts`. */
export const TASK_TOUR_SECTIONS: TaskTourSection[] = loadSections();
