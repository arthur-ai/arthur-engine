import { useEffect } from "react";

import { useTourEngine } from "@/features/tour";

/**
 * Headless: scrolls the active step's target into view when it resolves clipped
 * out of its scroll container, then re-checks occlusion so a covering
 * modal/drawer (now that the target is back in view) is detected and dismissed
 * by `OcclusionRecoveryWidget`.
 *
 * The engine intentionally does NOT scroll targets itself — its occlusion
 * detector treats a target with no viewport intersection as `offscreen` →
 * NOT-occluded → no recovery, no scroll. That strands targets inside
 * horizontally-scrolling containers, e.g. the playground prompt-card row: when
 * the docked tour side panel is open it narrows the page, so a duplicated card
 * overflows past the row's (now shorter) right edge and only a sliver shows.
 *
 * Visibility is judged against the target's effective clip rect — the viewport
 * intersected with every scroll-clipping ancestor — NOT the raw viewport. A card
 * whose box extends under the docked panel is still numerically inside
 * `innerWidth`, but it's clipped by its `overflow-x` row, so the viewport-only
 * check would wrongly call it visible. The widget is a no-op when the target is
 * already fully inside its clip, so it never introduces scroll jumps for the
 * common case.
 *
 * Reacts to `target:found`, which the engine emits only AFTER a step's
 * `reconcileSurfaces → navigate → prepare → resolve target` settle (and on every
 * `refreshTarget()`), so it never races the prepare/cleanup pipeline — the
 * element always exists by the time we scroll.
 */

// Sub-pixel tolerance so rounding / 1px borders don't read as "clipped".
const CLIP_TOLERANCE = 2;
// Let a smooth scroll settle before re-testing occlusion (one frame is too early
// for `behavior: "smooth"`). Covers the compound "off-screen AND covered" case.
const RECHECK_AFTER_MS = 350;

interface ClipRect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

/**
 * The viewport, tightened by every scroll-clipping (`overflow: auto | scroll`)
 * ancestor's box. This is the region the target can actually be visible in — a
 * scroll container narrower than the window (e.g. the playground card row when
 * the docked tour panel shrinks `<main>`) shrinks the clip accordingly.
 */
function getEffectiveClipRect(el: Element): ClipRect {
  const clip: ClipRect = {
    left: 0,
    top: 0,
    right: window.innerWidth || document.documentElement.clientWidth,
    bottom: window.innerHeight || document.documentElement.clientHeight,
  };
  let node = el.parentElement;
  while (node && node !== document.body && node !== document.documentElement) {
    const style = window.getComputedStyle(node);
    const clipsX = style.overflowX === "auto" || style.overflowX === "scroll";
    const clipsY = style.overflowY === "auto" || style.overflowY === "scroll";
    if (clipsX || clipsY) {
      const r = node.getBoundingClientRect();
      if (clipsX) {
        clip.left = Math.max(clip.left, r.left);
        clip.right = Math.min(clip.right, r.right);
      }
      if (clipsY) {
        clip.top = Math.max(clip.top, r.top);
        clip.bottom = Math.min(clip.bottom, r.bottom);
      }
    }
    node = node.parentElement;
  }
  return clip;
}

/**
 * Whether the target warrants scrolling into view, judged against its effective
 * clip rect. Full-bleed targets larger than the clip that already intersect it
 * (e.g. a whole panel) are left alone — centering them would jump with no gain.
 */
function shouldScrollIntoView(el: Element): boolean {
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return false; // detached / display:none — nothing to reveal
  const clip = getEffectiveClipRect(el);

  const intersectsW = Math.min(rect.right, clip.right) - Math.max(rect.left, clip.left);
  const intersectsH = Math.min(rect.bottom, clip.bottom) - Math.max(rect.top, clip.top);
  // No meaningful intersection — fully clipped out — always bring it in.
  if (intersectsW <= 1 || intersectsH <= 1) return true;
  // Larger than the clip in either axis and already intersecting — leave it.
  if (rect.width >= clip.right - clip.left || rect.height >= clip.bottom - clip.top) return false;
  // Smaller target whose box extends beyond the clip — center it back in.
  return (
    rect.left < clip.left - CLIP_TOLERANCE ||
    rect.top < clip.top - CLIP_TOLERANCE ||
    rect.right > clip.right + CLIP_TOLERANCE ||
    rect.bottom > clip.bottom + CLIP_TOLERANCE
  );
}

export function ScrollTargetIntoViewWidget() {
  const engine = useTourEngine();

  useEffect(() => {
    let recheckTimer = 0;

    const onTargetFound = (event: { element: Element }) => {
      const element = event.element;
      if (!element || typeof element.scrollIntoView !== "function" || typeof window === "undefined") return;
      if (!shouldScrollIntoView(element)) return;

      const reducedMotion = Boolean(window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches);
      // `inline: "center"` keeps a horizontally-scrolled card clear of the row's
      // edge so the step's side popover has room; `block: "nearest"` avoids
      // needless vertical movement when the target is already at the right height.
      element.scrollIntoView({ block: "nearest", inline: "center", behavior: reducedMotion ? "auto" : "smooth" });

      // After the scroll settles, re-test occlusion: a modal/drawer that was
      // covering the (previously clipped) target now reads as `covered`, so
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
