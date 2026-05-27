import { autoUpdate, flip, offset, shift, useFloating, type Placement, type ReferenceType, type VirtualElement } from "@floating-ui/react";
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
