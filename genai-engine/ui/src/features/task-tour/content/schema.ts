import { z } from "zod";

/**
 * Frontmatter shape for the optional `intro.hero` field — the marketing-facing
 * "section banner illustration" placed above the body prose.
 *
 * `src` is the path as written by marketing (`./assets/foo.png`). The loader
 * resolves it through `assetMap` after parsing; an unresolved path throws at
 * load time so a broken hero never silently disappears in production.
 */
export const HeroSchema = z.object({
  src: z.string().min(1, "intro.hero.src must be a non-empty path under ./assets/"),
  alt: z.string().min(1, "intro.hero.alt must be a non-empty alt text for accessibility"),
  width: z.number().positive().optional(),
});

export type HeroFrontmatter = z.infer<typeof HeroSchema>;

/**
 * Frontmatter shape for a single step entry inside a section file. The body
 * matches it via a `## step: <id>` heading; the loader cross-checks both.
 */
export const StepFrontmatterSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
});

export type StepFrontmatter = z.infer<typeof StepFrontmatterSchema>;

/**
 * Frontmatter shape for a section file (one of `00-intro.md` ... `06-deploy.md`).
 *
 * Holds every short, structured string the renderer needs — long prose lives
 * in the markdown body under `## intro`, `## scenario`, and `## step: <id>`
 * headings. Engineering wiring (targetId, route, eventName, advance) lives in
 * `content/wiring.ts` so marketing never sees it.
 */
export const SectionFrontmatterSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  kicker: z.string().min(1),
  intro: z.object({
    heading: z.string().min(1),
    cta: z.string().min(1),
    scenario: z
      .object({
        label: z.string().min(1),
      })
      .optional(),
    showFlywheel: z.boolean().optional(),
    hero: HeroSchema.optional(),
  }),
  steps: z.array(StepFrontmatterSchema).default([]),
});

export type SectionFrontmatter = z.infer<typeof SectionFrontmatterSchema>;

/**
 * Frontmatter shape for `_meta.md` — the top-level tour labels (modal title,
 * short name used in the resume FAB, dialog subtitle).
 */
export const MetaFrontmatterSchema = z.object({
  title: z.string().min(1),
  shortName: z.string().min(1),
  subtitle: z.string().min(1),
});

export type MetaFrontmatter = z.infer<typeof MetaFrontmatterSchema>;
