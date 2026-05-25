# Task Tour Content — Editing Guide

This directory holds the copy and imagery for the in-app **Evals 101** tour. Every file is editable by the marketing team without touching TypeScript.

Engineering wiring (which UI element each step points at, what event advances it, etc.) lives in `wiring.ts` and is owned by engineers. The two are merged automatically when the app loads.

---

## How edits ship

1. Edit a markdown file in this directory on a branch.
2. Run `yarn dev` from `genai-engine/ui/` and walk the tour to preview your changes.
3. Open a pull request — CI will catch frontmatter typos, missing assets, and step-id mismatches with a clear error message pointing at the offending file.

---

## File layout

```
content/
├── _meta.md              ← top-level tour title / subtitle / short name
├── 00-intro.md           ← Section 1
├── 01-agent.md           ← Section 2
├── 02-evals.md           ← Section 3
├── 03-traces.md          ← Section 4
├── 04-datasets.md        ← Section 5
├── 05-prompts.md         ← Section 6
├── 06-deploy.md          ← Section 7
├── README.md             ← (this file)
├── assets/               ← marketing-managed images
└── wiring.ts             ← engineering wiring (do not edit)
```

The numeric prefix on each filename (`00-`, `01-`, …) controls **tour order**. The `id:` field inside each file is the contract used by `wiring.ts` — don't change `id` without coordinating with engineering.

---

## Section file structure

Each section file is split into two parts:

- **Frontmatter** (between the `---` lines at the top) — short, structured strings.
- **Body** (everything below) — long-form prose under `## intro`, `## scenario`, and `## step: <id>` headings.

Here's the full schema with every supported field:

```markdown
---
id: evals # never change this without engineering
title: Look at evals # tab label / progress headline
kicker: Section 3 of 7 # small overline above the section heading
intro:
  heading: Measure before you change # big modal heading
  cta: Open Evaluate # primary button label in the modal
  showFlywheel: false # set to true for the ADLC flywheel diagram
  hero: # optional banner illustration
    src: ./assets/evals-banner.png
    alt: Screenshot of the Evaluate page
    width: 480 # optional, in pixels
  scenario: # optional "what you'll do" callout
    label: What you'll do
steps:
  - id: open-evaluate # must match a "## step: open-evaluate" below
    title: Open Evaluate # appears in the floating checklist
  - id: review-evaluator
    title: Review an evaluator
---

## intro

Long-form prose that appears in the section's welcome modal. Supports **bold**,
_italic_, [links](https://docs.arthur.ai), inline `code`, lists, and images.

## scenario

Required only when `intro.scenario.label` is set above. This text appears in
the dashed callout box at the bottom of the modal.

## step: open-evaluate

Instructions for the first step. Marketing controls this prose; engineering
controls which UI element the spotlight points at (see wiring.ts).

## step: review-evaluator

Instructions for the second step. Each `## step: <id>` heading must match a
step entry in the frontmatter above and an entry in wiring.ts.
```

---

## Supported markdown

All of the following work inside `## intro`, `## scenario`, and `## step: <id>` body blocks:

| Syntax                     | Renders as                      |
| -------------------------- | ------------------------------- |
| `**bold**`                 | **bold**                        |
| `*italic*`                 | _italic_                        |
| `` `inline code` ``        | `inline code`                   |
| `[label](https://...)`     | external link, opens in new tab |
| `- bullet`                 | unordered list                  |
| `1. ordered`               | ordered list                    |
| `![alt](./assets/foo.png)` | inline image (see Images below) |

**Don't use** (will be stripped, dropped, or break the build):

- Unsafe HTML — `<script>`, `<iframe>`, event handlers like `onclick=`, and `javascript:` links are sanitized out at render time.
- Other raw HTML — even safe tags like `<div>`/`<details>`/`<table>` written as literal HTML are best avoided. Use markdown syntax instead; the renderer's element set is fixed.
- Headings inside body blocks — don't use `# title` or `### subheading` inside `## intro`. The `##` markers are reserved for the section structure.
- Duplicate `## intro`, `## scenario`, or `## step: <id>` headings — the loader throws on duplicates so a copy-paste typo gets caught immediately.
- Remote image URLs (`https://example.com/foo.png`) — images must live in `./assets/`.

---

## Images

### Adding an image

1. Drop the file into `content/assets/`. Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`, `.avif`. Prefer `.svg` for diagrams and `.webp`/`.avif` for screenshots — they're smaller than `.png`.
2. Reference it from markdown by relative path: `./assets/<filename>`.
3. Optimize before committing (compress PNGs, simplify SVGs).

### Two ways to use an image

**1. Hero banner — `intro.hero` frontmatter field.** One image per section, placed above the intro body, sized consistently. Use this for section-level illustrations and screenshots.

```yaml
intro:
  hero:
    src: ./assets/datasets-hero.png
    alt: A dataset table with three rows highlighted
    width: 480
```

**2. Inline image — `![]()` syntax inside any body block.** For images embedded in prose, screenshots inside step instructions, etc.

```markdown
## step: open-evaluate

Click **Evaluate** in the sidebar. It looks like this:

![The Evaluate menu item](./assets/sidebar-evaluate.png)
```

### What happens if an image is missing?

- **`intro.hero.src` doesn't exist** → the section fails to load loudly, with a clear error message pointing at the missing file. The tour won't ship broken.
- **`![]()` inline image doesn't exist** → the image is silently dropped (so a typo in one step doesn't break the whole tour), and a warning appears in the browser console during development.

---

## Common pitfalls

- **Step id renames** require coordinating with engineering. The id is referenced from `wiring.ts`; both files must change together.
- **Removing a step** means deleting both the frontmatter entry _and_ the `## step: <id>` body block.
- **The dev server caches markdown changes** — save the file and your changes appear immediately. No restart needed.
- **YAML indentation matters** in the frontmatter. Use 2 spaces, no tabs.

---

## Tour-level labels — `_meta.md`

`_meta.md` controls the three labels that aren't tied to a single section:

```yaml
---
title: "Evals 101: Build a Production-Grade Agent" # full modal title
shortName: "Evals 101" # resume-FAB label
subtitle: "A guided tour of the Arthur Development Lifecycle (ADLC)"
---
```

The body of `_meta.md` is treated as comments.
