import type { CSSProperties, MouseEvent, ReactNode } from "react";

import type { HighlightSpec, OverlayConfig, TourActions } from "../../core/types";

export interface BackdropBlockerProps {
  cutoutRect: DOMRect | null;
  padding?: number;
  onBackdropClick?: (event: MouseEvent<HTMLDivElement>) => void;
  style?: CSSProperties;
  className?: string;
}

/**
 * Pointer-blocking layer that frames the spotlight cutout with four
 * transparent panels. Pair with `Spotlight` for the visual dim.
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

export function getHighlightPadding(spec: HighlightSpec | undefined): number {
  if (!spec) return 8;
  switch (spec.shape) {
    case "box":
    case "circle":
    case "custom":
      return spec.padding ?? 8;
    case "none":
      return 0;
    default:
      return 8;
  }
}

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
