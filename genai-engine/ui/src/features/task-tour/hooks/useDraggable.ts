import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/**
 * Shared drag-to-reposition behavior for the tour's floating surfaces (the
 * resume FAB and the checklist panel). Tracks a `{ left, bottom }` position
 * pinned to the viewport, persists it to `localStorage`, clamps it back into
 * view on resize, and distinguishes a tap from a drag via a small movement
 * threshold so a click still acts as a click.
 *
 * Positions are stored as distance from the left/bottom viewport edges so a
 * surface anchored to the bottom of the screen grows upward and stays put when
 * the window height changes.
 */
export interface DraggablePosition {
  left: number;
  bottom: number;
}

const DRAG_THRESHOLD_PX = 5;
const VIEWPORT_MARGIN_PX = 8;

interface UseDraggableOptions {
  /** `localStorage` key under which the position is persisted. */
  storageKey: string;
  /** Fallback position used when nothing is stored (evaluated lazily). */
  defaultPosition: DraggablePosition | (() => DraggablePosition);
  /**
   * Invoked on a pointer release that did NOT cross the drag threshold. Use
   * for surfaces whose whole body is the click target (e.g. the FAB). Omit
   * for surfaces that keep their own native `onClick` — the returned
   * `onClickCapture` guard suppresses the click that follows a real drag.
   */
  onClick?: () => void;
  /** When false, the surface is locked in place and pointer handlers no-op. */
  enabled?: boolean;
}

function resolveDefault(defaultPosition: DraggablePosition | (() => DraggablePosition)): DraggablePosition {
  return typeof defaultPosition === "function" ? defaultPosition() : defaultPosition;
}

function readStoredPosition(storageKey: string, fallback: DraggablePosition): DraggablePosition {
  if (typeof window === "undefined") {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return fallback;
    }

    const parsed: unknown = JSON.parse(raw);
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "left" in parsed &&
      "bottom" in parsed &&
      typeof parsed.left === "number" &&
      typeof parsed.bottom === "number"
    ) {
      return { left: parsed.left, bottom: parsed.bottom };
    }
  } catch {
    // Ignore malformed storage and fall back to the default corner.
  }

  return fallback;
}

function clampPosition(position: DraggablePosition, width: number, height: number): DraggablePosition {
  const maxLeft = window.innerWidth - width - VIEWPORT_MARGIN_PX;
  const maxBottom = window.innerHeight - height - VIEWPORT_MARGIN_PX;

  return {
    left: Math.max(VIEWPORT_MARGIN_PX, Math.min(position.left, maxLeft)),
    bottom: Math.max(VIEWPORT_MARGIN_PX, Math.min(position.bottom, maxBottom)),
  };
}

export interface DraggableHandleProps {
  onPointerDown: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerMove: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerUp: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerCancel: (event: React.PointerEvent<HTMLElement>) => void;
  onClickCapture: (event: React.MouseEvent<HTMLElement>) => void;
}

export interface UseDraggableResult<T extends HTMLElement> {
  position: DraggablePosition;
  isDragging: boolean;
  /** Ref for the element measured when clamping to the viewport. */
  ref: React.RefObject<T | null>;
  /** Spread onto the drag affordance (whole body, or just a header handle). */
  handleProps: DraggableHandleProps;
}

export function useDraggable<T extends HTMLElement = HTMLElement>({
  storageKey,
  defaultPosition,
  onClick,
  enabled = true,
}: UseDraggableOptions): UseDraggableResult<T> {
  const elementRef = useRef<T>(null);
  const dragStateRef = useRef<{
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startLeft: number;
    startBottom: number;
    didDrag: boolean;
  } | null>(null);
  // Set when a drag completes so the synthetic click that follows is swallowed.
  const suppressClickRef = useRef(false);

  const [position, setPosition] = useState<DraggablePosition>(() => readStoredPosition(storageKey, resolveDefault(defaultPosition)));
  const [isDragging, setIsDragging] = useState(false);

  const persistPosition = useCallback(
    (next: DraggablePosition) => {
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(next));
      } catch {
        // Ignore quota / privacy-mode failures.
      }
    },
    [storageKey]
  );

  const clampCurrentPosition = useCallback(
    (next: DraggablePosition, persist = false) => {
      const element = elementRef.current;
      const clamped = element ? clampPosition(next, element.offsetWidth, element.offsetHeight) : next;

      setPosition(clamped);
      if (persist) {
        persistPosition(clamped);
      }
    },
    [persistPosition]
  );

  // Re-clamp the stored position once the element has measurable dimensions,
  // and again whenever the surface is re-enabled (e.g. it remounts at a new
  // size). Keeps a position saved on a larger viewport from spilling off a
  // smaller one.
  useLayoutEffect(() => {
    if (!enabled) return;
    clampCurrentPosition(readStoredPosition(storageKey, resolveDefault(defaultPosition)), true);
    // `defaultPosition` is intentionally read fresh rather than tracked as a dep
    // to avoid re-clamping on every render from an inline default factory.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, storageKey, clampCurrentPosition]);

  useEffect(() => {
    if (!enabled) return;
    const handleResize = () => {
      setPosition((prev) => {
        const element = elementRef.current;
        if (!element) {
          return prev;
        }

        const clamped = clampPosition(prev, element.offsetWidth, element.offsetHeight);
        persistPosition(clamped);
        return clamped;
      });
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [enabled, persistPosition]);

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if (!enabled || event.button !== 0) {
        return;
      }

      dragStateRef.current = {
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        startLeft: position.left,
        startBottom: position.bottom,
        didDrag: false,
      };

      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [enabled, position.left, position.bottom]
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      const dragState = dragStateRef.current;
      if (!dragState || dragState.pointerId !== event.pointerId) {
        return;
      }

      const deltaX = event.clientX - dragState.startClientX;
      const deltaY = event.clientY - dragState.startClientY;

      if (!dragState.didDrag && Math.hypot(deltaX, deltaY) >= DRAG_THRESHOLD_PX) {
        dragState.didDrag = true;
        setIsDragging(true);
      }

      if (!dragState.didDrag) {
        return;
      }

      clampCurrentPosition({
        left: dragState.startLeft + deltaX,
        bottom: dragState.startBottom - deltaY,
      });
    },
    [clampCurrentPosition]
  );

  const finishDrag = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      const dragState = dragStateRef.current;
      if (!dragState || dragState.pointerId !== event.pointerId) {
        return;
      }

      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }

      if (dragState.didDrag) {
        // Swallow the click the browser fires after the drag so it doesn't
        // trigger the surface's own onClick (e.g. expanding the panel).
        suppressClickRef.current = true;
        setPosition((prev) => {
          const element = elementRef.current;
          const clamped = element ? clampPosition(prev, element.offsetWidth, element.offsetHeight) : prev;
          persistPosition(clamped);
          return clamped;
        });
      } else {
        onClick?.();
      }

      dragStateRef.current = null;
      setIsDragging(false);
    },
    [onClick, persistPosition]
  );

  const handleClickCapture = useCallback((event: React.MouseEvent<HTMLElement>) => {
    if (suppressClickRef.current) {
      event.preventDefault();
      event.stopPropagation();
      suppressClickRef.current = false;
    }
  }, []);

  return {
    position,
    isDragging,
    ref: elementRef,
    handleProps: {
      onPointerDown: handlePointerDown,
      onPointerMove: handlePointerMove,
      onPointerUp: finishDrag,
      onPointerCancel: finishDrag,
      onClickCapture: handleClickCapture,
    },
  };
}
