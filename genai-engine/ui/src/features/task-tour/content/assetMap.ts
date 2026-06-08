/**
 * Build-time map of marketing-managed image assets so markdown body content
 * and `intro.hero` frontmatter can reference local files by relative path.
 *
 * Marketing drops images into `./assets/`, then references them as
 * `./assets/<filename>` (or just `assets/<filename>`) from markdown. The map
 * keys are the relative paths as written by marketing; values are the
 * Vite-resolved URLs (hashed and fingerprinted for production builds).
 *
 * `import.meta.glob` evaluates at build time, so the lookup is a pure object
 * read at runtime — no async, no race conditions.
 */
const rawAssets = import.meta.glob("./assets/*.{png,jpg,jpeg,gif,svg,webp,avif}", {
  eager: true,
  query: "?url",
  import: "default",
}) as Record<string, string>;

/**
 * Normalize a marketing-supplied path into the canonical form used as the
 * asset-map key (`./assets/<filename>`). Accepts the variants `./assets/foo`,
 * `assets/foo`, and `/assets/foo` so authors don't have to be precise.
 */
function normalize(srcPath: string): string {
  let path = srcPath.trim();
  if (path.startsWith("/")) path = path.slice(1);
  if (!path.startsWith("./")) path = `./${path}`;
  return path;
}

/**
 * Canonicalized map of `./assets/<filename>` → hashed Vite URL. Iterating
 * `rawAssets` keys here ensures everything stored matches what callers will
 * look up via `normalize`.
 */
export const TASK_TOUR_ASSET_MAP: Readonly<Record<string, string>> = Object.fromEntries(
  Object.entries(rawAssets).map(([key, url]) => [normalize(key), url])
);

/** Returns true for any path that should never be resolved through the asset map. */
function isRemote(srcPath: string): boolean {
  return /^(https?:)?\/\//i.test(srcPath) || srcPath.startsWith("data:") || srcPath.startsWith("blob:");
}

/**
 * Resolve a marketing-supplied image path against the asset map.
 *
 * Returns `null` for remote URLs and unresolved local paths so callers can
 * either drop the element (markdown body images — typo-tolerant) or throw
 * (frontmatter `intro.hero` — load-time validated).
 */
export function resolveAssetSrc(srcPath: string | undefined | null): string | null {
  if (!srcPath) return null;
  if (isRemote(srcPath)) return null;
  return TASK_TOUR_ASSET_MAP[normalize(srcPath)] ?? null;
}
