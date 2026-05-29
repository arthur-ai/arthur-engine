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
      flip({ padding: viewportPadding, fallbackAxisSideDirection: "end" }),
      // `crossAxis: true` lets the popover slide along the placement's cross
      // axis too, so when the target nearly fills the viewport (e.g. the trace
      // drawer actions region) and no outside side fits, the popover is pulled
      // back into the viewport — overlapping the target rather than clipping
      // off-screen. The limiter still constrains the main axis (keeps the
      // popover attached to the target side) but leaves the cross axis free so
      // it can travel all the way inside when needed.
      shift({ padding: viewportPadding, crossAxis: true, limiter: limitShift({ crossAxis: false }) }),
      // Cap the popover to the space actually available in its final placement
      // so it never spills outside the viewport; long content scrolls inside.
      size({
        padding: viewportPadding,
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
