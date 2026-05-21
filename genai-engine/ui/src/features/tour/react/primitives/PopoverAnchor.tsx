import { autoUpdate, flip, offset, shift, useFloating, type Placement, type ReferenceType, type VirtualElement } from "@floating-ui/react";
import { useEffect, useMemo, type CSSProperties, type ReactNode } from "react";

export interface PopoverAnchorProps {
  rect: DOMRect | null;
  placement?: Placement;
  /** px offset between the popover and the anchor rect. Default 12. */
  offset?: number;
  /** px padding from the viewport edge. Default 12. */
  viewportPadding?: number;
  /** Inline style escape hatch (z-index, etc.). */
  style?: CSSProperties;
  className?: string;
  children: ReactNode;
}

/**
 * Positions `children` relative to the live target rect via floating-ui. The
 * rect is wrapped in a virtual reference element and assigned via
 * `refs.setReference()` (the `elements.reference` field in @floating-ui/react
 * is restricted to Element, so we use the imperative setter for the virtual
 * case).
 *
 * Renders nothing while `rect` is null.
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
    middleware: [offset(gap), flip(), shift({ padding: viewportPadding })],
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
