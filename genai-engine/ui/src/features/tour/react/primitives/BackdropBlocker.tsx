import type { CSSProperties, MouseEvent, ReactNode } from "react";

import type { HighlightSpec, OverlayConfig, TourActions } from "../../core/types";

export interface BackdropBlockerProps {
  /**
   * Rectangle that should remain interactive (typically the active target's
   * bounding rect). When null, the entire viewport is blocked — useful when
   * combined with `highlight.shape === "none"`.
   */
  cutoutRect: DOMRect | null;
  /**
   * Padding around the cutout that should also remain interactive. Should
   * match the visual `Spotlight` padding so the visible cutout and the
   * clickable area line up. Default 8.
   */
  padding?: number;
  /** Click handler invoked when the user clicks any of the four blocker panels. */
  onBackdropClick?: (event: MouseEvent<HTMLDivElement>) => void;
  /**
   * Inline style escape hatch for the rendered panels (z-index, transitions,
   * background color, etc.). The blocker itself is intentionally transparent —
   * pair it with `Spotlight` for the visual dim.
   */
  style?: CSSProperties;
  className?: string;
}

/**
 * Pointer-blocking layer that frames the spotlight cutout with four invisible
 * panels (top / bottom / left / right). Each panel has `pointer-events: auto`
 * so clicks outside the cutout are absorbed; the cutout area itself has no
 * panel, allowing clicks to fall through to the highlighted target.
 *
 * Pair this with the visual `Spotlight` to focus the user on a single part of
 * the page. Render it below the popover in z-index order so the popover stays
 * interactive.
 *
 * When `cutoutRect` is null a single full-viewport panel is rendered, which is
 * the natural pairing for `highlight.shape === "none"`.
 */
export function BackdropBlocker({ cutoutRect, padding = 8, onBackdropClick, style, className }: BackdropBlockerProps): ReactNode {
  const baseStyle: CSSProperties = {
    position: "fixed",
    pointerEvents: "auto",
    background: "transparent",
    ...style,
  };

  if (!cutoutRect) {
    return <div aria-hidden="true" className={className} onClick={onBackdropClick} style={{ ...baseStyle, inset: 0 }} />;
  }

  const top = Math.max(0, cutoutRect.y - padding);
  const left = Math.max(0, cutoutRect.x - padding);
  const bottom = Math.max(0, cutoutRect.y + cutoutRect.height + padding);
  const right = Math.max(0, cutoutRect.x + cutoutRect.width + padding);
  const middleHeight = Math.max(0, bottom - top);

  return (
    <>
      <div aria-hidden="true" className={className} onClick={onBackdropClick} style={{ ...baseStyle, top: 0, left: 0, right: 0, height: top }} />
      <div aria-hidden="true" className={className} onClick={onBackdropClick} style={{ ...baseStyle, top: bottom, left: 0, right: 0, bottom: 0 }} />
      <div
        aria-hidden="true"
        className={className}
        onClick={onBackdropClick}
        style={{ ...baseStyle, top, left: 0, width: left, height: middleHeight }}
      />
      <div
        aria-hidden="true"
        className={className}
        onClick={onBackdropClick}
        style={{ ...baseStyle, top, left: right, right: 0, height: middleHeight }}
      />
    </>
  );
}

/**
 * Picks the padding the `Spotlight` would apply for a given highlight, so
 * `BackdropBlocker` can match it pixel-for-pixel. Mirrors the defaults in
 * `Spotlight.normalize`.
 */
export function getHighlightPadding(spec: HighlightSpec | undefined): number {
  if (!spec) return 8;
  switch (spec.shape) {
    case "box":
    case "circle":
      return spec.padding ?? 8;
    case "none":
      return 0;
    default:
      return 8;
  }
}

/**
 * Maps an `OverlayConfig["onBackdropClick"]` declaration to the matching call
 * on the engine's `TourActions`. Lives here so any UI layer (the default or a
 * custom scene like `ChecklistTour`) can honor the same config field with one
 * line.
 */
export function applyBackdropAction(action: OverlayConfig["onBackdropClick"], actions: TourActions): void {
  switch (action) {
    case "next":
      actions.next();
      return;
    case "skip":
      actions.skip();
      return;
    case "dismiss":
      actions.dismiss();
      return;
    case "none":
    case undefined:
    default:
      return;
  }
}
