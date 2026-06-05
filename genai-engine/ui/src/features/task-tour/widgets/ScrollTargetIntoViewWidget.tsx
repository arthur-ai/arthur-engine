import { useEffect } from "react";

import { useTourEngine } from "@/features/tour";

/**
 * Headless: scrolls the active step's target into view when it resolves
 * off-screen, then re-checks occlusion so a covering modal/drawer (now that the
 * target is back in the viewport) is detected and dismissed by
 * `OcclusionRecoveryWidget`.
 *
 * The engine intentionally does NOT scroll targets itself — its occlusion
 * detector treats a target with no viewport intersection as `offscreen` →
 * NOT-occluded → no recovery, no scroll. That strands targets inside
 * horizontally-scrolling containers (e.g. the playground prompt-card row, where
 * a duplicated card sits past the right edge). This widget closes that gap
 * generically for every step: it's a no-op when the target is already
 * comfortably visible, so it never introduces scroll jumps for the common case.
 *
 * Reacts to `target:found`, which the engine emits only AFTER a step's
 * `reconcileSurfaces → navigate → prepare → resolve target` settle (and on every
 * `refreshTarget()`), so it never races the prepare/cleanup pipeline — the
 * element always exists by the time we scroll.
 */

// Slack (px) around the viewport edges before a smaller target counts as clipped.
// Keeps the widget a no-op for targets merely flush against an edge.
const VISIBILITY_MARGIN = 8;
// Let a smooth scroll settle before re-testing occlusion (one frame is too early
// for `behavior: "smooth"`). Covers the compound "off-screen AND covered" case.
const RECHECK_AFTER_MS = 350;

/**
 * Whether `rect` warrants scrolling into view. Mirrors the engine's own
 * `offscreen` definition for the fully-hidden case, while also centering a
 * partially-clipped small target. Full-bleed targets larger than the viewport
 * (e.g. a whole panel) that already intersect are left alone — centering them
 * would jump the page with no benefit.
 */
function shouldScrollIntoView(rect: DOMRect, viewportW: number, viewportH: number): boolean {
  const intersectsW = Math.min(rect.right, viewportW) - Math.max(rect.left, 0);
  const intersectsH = Math.min(rect.bottom, viewportH) - Math.max(rect.top, 0);
  // Fully (or all-but-a-sliver) off-screen — always bring it in.
  if (intersectsW <= 1 || intersectsH <= 1) return true;
  // Larger than the viewport in either axis and already intersecting — leave it.
  if (rect.width >= viewportW || rect.height >= viewportH) return false;
  // Smaller target clipped past the margin — center it.
  return (
    rect.left < VISIBILITY_MARGIN ||
    rect.top < VISIBILITY_MARGIN ||
    rect.right > viewportW - VISIBILITY_MARGIN ||
    rect.bottom > viewportH - VISIBILITY_MARGIN
  );
}

export function ScrollTargetIntoViewWidget() {
  const engine = useTourEngine();

  useEffect(() => {
    let recheckTimer = 0;

    const onTargetFound = (event: { element: Element }) => {
      const element = event.element;
      if (!element || typeof element.scrollIntoView !== "function" || typeof window === "undefined") return;

      const viewportW = window.innerWidth || document.documentElement.clientWidth;
      const viewportH = window.innerHeight || document.documentElement.clientHeight;
      if (!shouldScrollIntoView(element.getBoundingClientRect(), viewportW, viewportH)) return;

      const reducedMotion = Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
      // `inline: "center"` keeps a horizontally-scrolled card off the edge so the
      // step's side popover has room; `block: "nearest"` avoids needless vertical
      // movement when the target is already at the right height.
      element.scrollIntoView({ block: "nearest", inline: "center", behavior: reducedMotion ? "auto" : "smooth" });

      // After the scroll settles, re-test occlusion: a modal/drawer that was
      // covering the (previously off-screen) target now reads as `covered`, so
      // OcclusionRecoveryWidget can dismiss it.
      window.clearTimeout(recheckTimer);
      recheckTimer = window.setTimeout(() => engine.recheckOcclusion(), RECHECK_AFTER_MS);
    };

    engine.on("target:found", onTargetFound);
    return () => {
      engine.off("target:found", onTargetFound);
      if (typeof window !== "undefined") window.clearTimeout(recheckTimer);
    };
  }, [engine]);

  return null;
}
