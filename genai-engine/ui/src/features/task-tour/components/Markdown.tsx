import { Box, Link, Typography, type TypographyProps } from "@mui/material";
import type { Schema } from "hast-util-sanitize";
import { useMemo, type ImgHTMLAttributes, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import type { PluggableList } from "unified";

import { resolveAssetSrc } from "../content/assetMap";

/**
 * Variants drive the surrounding text-size context. `body2` is the standard
 * paragraph used inside `SectionIntroDialog`; `caption` is the smaller
 * typography we use for step instructions inside the checklist panel.
 */
export type MarkdownVariant = Extract<TypographyProps["variant"], "body2" | "caption">;

export interface MarkdownProps {
  children: string;
  /** Controls the typography variant used for paragraphs / list text. */
  variant?: MarkdownVariant;
  /** Optional className passthrough for layout/spacing tweaks at the call site. */
  className?: string;
}

/**
 * Sanitization schema. Starts from `defaultSchema` (GitHub-style allowlist),
 * then permits the small set of `<img>` attributes we need for marketing
 * imagery. Raw HTML, scripts, and forms remain forbidden by inheritance.
 */
const SANITIZE_SCHEMA: Schema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    img: [...(defaultSchema.attributes?.img ?? []), "src", "alt", "width", "height", "loading"],
    a: [...(defaultSchema.attributes?.a ?? []), "title"],
  },
};

const REMARK_PLUGINS: PluggableList = [remarkGfm];
const REHYPE_PLUGINS: PluggableList = [[rehypeSanitize, SANITIZE_SCHEMA]];

/**
 * Build the element-override map for a given typography variant. Memoized in
 * the component so identical variants reuse the same component object across
 * renders (avoids re-instantiating react-markdown's internal walker).
 */
function buildComponents(variant: MarkdownVariant): Components {
  return {
    p: ({ children }) => (
      <Typography component="p" variant={variant} sx={{ color: "inherit", lineHeight: 1.55, "&:not(:last-child)": { mb: 1 } }}>
        {children}
      </Typography>
    ),
    a: ({ href, title, children }) => (
      <Link
        href={href ?? "#"}
        title={title}
        target="_blank"
        rel="noreferrer noopener"
        underline="hover"
        sx={{ color: "secondary.main", fontWeight: 500 }}
      >
        {children}
      </Link>
    ),
    strong: ({ children }) => (
      <Box component="strong" sx={{ fontWeight: 600 }}>
        {children}
      </Box>
    ),
    em: ({ children }) => (
      <Box component="em" sx={{ fontStyle: "italic" }}>
        {children}
      </Box>
    ),
    ul: ({ children }) => (
      <Box component="ul" sx={{ pl: 2.25, my: 0.5, "& > li + li": { mt: 0.25 } }}>
        {children}
      </Box>
    ),
    ol: ({ children }) => (
      <Box component="ol" sx={{ pl: 2.25, my: 0.5, "& > li + li": { mt: 0.25 } }}>
        {children}
      </Box>
    ),
    li: ({ children }) => (
      <Typography component="li" variant={variant} sx={{ color: "inherit", lineHeight: 1.55 }}>
        {children}
      </Typography>
    ),
    code: ({ children }) => (
      <Box
        component="code"
        sx={{
          fontFamily: "monospace",
          fontSize: "0.9em",
          px: 0.5,
          py: 0.1,
          borderRadius: 0.5,
          bgcolor: "action.hover",
          color: "text.primary",
        }}
      >
        {children}
      </Box>
    ),
    img: ImgWithAssetMap,
  };
}

/**
 * Markdown `<img>` override. Marketing references images by relative path
 * (e.g. `./assets/foo.png`); we resolve those against the Vite-built asset
 * map so production gets hashed URLs and dev gets live-reloaded paths.
 *
 * Unresolved sources (remote URLs, typos, missing assets) render nothing and
 * emit a dev-only warning. This is intentionally typo-tolerant for body
 * content — a broken image inside a step shouldn't take down the whole tour.
 * The frontmatter `intro.hero` field is validated separately at load time
 * and throws on miss.
 */
function ImgWithAssetMap({ src, alt, width, height }: ImgHTMLAttributes<HTMLImageElement>): ReactNode {
  const resolved = typeof src === "string" ? resolveAssetSrc(src) : null;
  if (!resolved) {
    if (import.meta.env.DEV) {
      console.warn(`[task-tour:Markdown] dropping <img src="${String(src)}"> — not found in content/assets`);
    }
    return null;
  }
  return (
    <Box
      component="img"
      src={resolved}
      alt={alt ?? ""}
      width={width}
      height={height}
      loading="lazy"
      sx={{
        display: "block",
        maxWidth: "100%",
        height: "auto",
        my: 1,
        mx: "auto",
        borderRadius: 1,
      }}
    />
  );
}

/**
 * Render sanitized markdown using the task-tour theming.
 *
 * - GitHub-style markdown (via `remark-gfm`) — supports tables, strikethrough,
 *   task lists, autolinks.
 * - Sanitized with the default GitHub allowlist, extended only for the `<img>`
 *   attributes the marketing imagery needs.
 * - Inline `![alt](./assets/foo.png)` references are resolved against the
 *   build-time asset map; unresolved entries are dropped.
 */
export function Markdown({ children, variant = "body2", className }: MarkdownProps) {
  const components = useMemo(() => buildComponents(variant), [variant]);
  return (
    <Box className={className} sx={{ color: "inherit" }}>
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} rehypePlugins={REHYPE_PLUGINS} components={components}>
        {children}
      </ReactMarkdown>
    </Box>
  );
}
