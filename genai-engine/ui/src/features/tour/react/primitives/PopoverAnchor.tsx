import {
  autoUpdate,
  flip,
  limitShift,
  offset,
  shift,
  size,
  useFloating,
  type Placement,
  type ReferenceType,
  type VirtualElement,
} from "@floating-ui/react";
import { useEffect, useMemo, type CSSProperties, type ReactNode } from "react";

export interface PopoverAnchorProps {
  rect: DOMRect | null;
  placement?: Placement;
  offset?: number;
  viewportPadding?: number;
  style?: CSSProperties;
  className?: string;
  children: ReactNode;
}

// Width the docked checklist panel reserves on the right, published by
// `TourSidePanel` and subtracted by MUI dialogs/drawers too (see `mui-theme.ts`).
// 0 outside the tour, where the variable is unset.
function readInsetRight(): number {
  if (typeof window === "undefined") return 0;
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--app-inset-right");
  const value = parseFloat(raw);
  return Number.isFinite(value) ? value : 0;
}

/**
 * Positions `children` relative to a live rect via floating-ui. Renders
 * nothing while `rect` is null.
 */
export function PopoverAnchor({
  rect,
  placement = "bottom",
  offset: gap = 12,
  viewportPadding = 12,
  style,
  className,
  children,
}: PopoverAnchorProps) {
  // Trim the checklist panel's column off the right edge so the popover never
  // lands on top of it (UP-4548). Re-read each render; the rect re-measures and
  // re-renders us as the panel's collapse/expand animation reflows the page.
  const insetRight = readInsetRight();
  const padding = { top: viewportPadding, right: viewportPadding + insetRight, bottom: viewportPadding, left: viewportPadding };

  const { refs, floatingStyles } = useFloating<ReferenceType>({
    placement,
    strategy: "fixed",
    whileElementsMounted: autoUpdate,
    middleware: [
      offset(gap),
      // `fallbackAxisSideDirection` lets the popover switch to a perpendicular
      // side (e.g. top -> right) when neither the preferred side nor its
      // opposite fits — important for very tall targets like the evaluator
      // instructions panel or the full-height version drawer.
      flip({ padding, fallbackAxisSideDirection: "end" }),
      // `crossAxis: true` lets the popover slide along the placement's cross
      // axis too, so when the target nearly fills the viewport (e.g. the trace
      // drawer actions region) and no outside side fits, the popover is pulled
      // back into the viewport — overlapping the target rather than clipping
      // off-screen. The limiter still constrains the main axis (keeps the
      // popover attached to the target side) but leaves the cross axis free so
      // it can travel all the way inside when needed.
      shift({ padding, crossAxis: true, limiter: limitShift({ crossAxis: false }) }),
      // Cap the popover to the space actually available in its final placement
      // so it never spills outside the viewport; long content scrolls inside.
      size({
        padding,
        apply({ availableWidth, availableHeight, elements }) {
          Object.assign(elements.floating.style, {
            maxWidth: `${Math.max(200, availableWidth)}px`,
            maxHeight: `${Math.max(160, availableHeight)}px`,
            overflowY: "auto",
            overflowX: "hidden",
          });
        },
      }),
    ],
  });

  const reference = useMemo<VirtualElement | null>(() => {
    if (!rect) return null;
    return {
      getBoundingClientRect: () => rect,
      contextElement: typeof document !== "undefined" ? document.body : undefined,
    };
  }, [rect]);

  useEffect(() => {
    refs.setReference(reference);
  }, [refs, reference]);

  if (!rect) return null;

  return (
    <div ref={refs.setFloating} className={className} style={{ ...floatingStyles, ...style }}>
      {children}
    </div>
  );
}
