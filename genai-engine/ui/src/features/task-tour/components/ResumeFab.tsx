import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { Fab, useTheme } from "@mui/material";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

export interface ResumeFabProps {
  onClick: () => void;
  /** Called whenever the FAB's screen rect changes (move, resize, scroll). */
  onAnchorRectChange?: (rect: DOMRect | null) => void;
}

const STORAGE_KEY = "task-tour:resume-fab-position";
const DRAG_THRESHOLD_PX = 5;
const VIEWPORT_MARGIN_PX = 8;
const DEFAULT_POSITION = { left: 20, bottom: 20 };

interface FabPosition {
  left: number;
  bottom: number;
}

function readStoredPosition(): FabPosition {
  if (typeof window === "undefined") {
    return DEFAULT_POSITION;
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_POSITION;
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

  return DEFAULT_POSITION;
}

function clampPosition(position: FabPosition, width: number, height: number): FabPosition {
  const maxLeft = window.innerWidth - width - VIEWPORT_MARGIN_PX;
  const maxBottom = window.innerHeight - height - VIEWPORT_MARGIN_PX;

  return {
    left: Math.max(VIEWPORT_MARGIN_PX, Math.min(position.left, maxLeft)),
    bottom: Math.max(VIEWPORT_MARGIN_PX, Math.min(position.bottom, maxBottom)),
  };
}

/**
 * Bottom-left floating action button that re-opens a dismissed tour. Draggable
 * so users can move it out of the way; position is persisted across sessions.
 * Styled with the same brand-purple accent as the spotlight ring.
 */
export function ResumeFab({ onClick, onAnchorRectChange }: ResumeFabProps) {
  const theme = useTheme();
  const fabRef = useRef<HTMLButtonElement>(null);
  const dragStateRef = useRef<{
    pointerId: number;
    startClientX: number;
    startClientY: number;
    startLeft: number;
    startBottom: number;
    didDrag: boolean;
  } | null>(null);

  const [position, setPosition] = useState<FabPosition>(() => readStoredPosition());
  const [isDragging, setIsDragging] = useState(false);

  const persistPosition = useCallback((next: FabPosition) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Ignore quota / privacy-mode failures.
    }
  }, []);

  const reportAnchorRect = useCallback(() => {
    onAnchorRectChange?.(fabRef.current?.getBoundingClientRect() ?? null);
  }, [onAnchorRectChange]);

  const clampCurrentPosition = useCallback(
    (next: FabPosition, persist = false) => {
      const element = fabRef.current;
      const clamped = element ? clampPosition(next, element.offsetWidth, element.offsetHeight) : next;

      setPosition(clamped);
      if (persist) {
        persistPosition(clamped);
      }
    },
    [persistPosition],
  );

  useLayoutEffect(() => {
    clampCurrentPosition(readStoredPosition(), true);
  }, [clampCurrentPosition]);

  useLayoutEffect(() => {
    reportAnchorRect();
  }, [position, reportAnchorRect]);

  useEffect(() => {
    if (!onAnchorRectChange) {
      return;
    }

    const element = fabRef.current;
    if (!element) {
      return;
    }

    const resizeObserver = new ResizeObserver(reportAnchorRect);
    resizeObserver.observe(element);
    window.addEventListener("scroll", reportAnchorRect, true);
    window.addEventListener("resize", reportAnchorRect);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("scroll", reportAnchorRect, true);
      window.removeEventListener("resize", reportAnchorRect);
    };
  }, [onAnchorRectChange, reportAnchorRect]);

  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => {
        const element = fabRef.current;
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
  }, [persistPosition]);

  const handlePointerDown = (event: React.PointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0) {
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
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLButtonElement>) => {
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
  };

  const finishDrag = (event: React.PointerEvent<HTMLButtonElement>) => {
    const dragState = dragStateRef.current;
    if (!dragState || dragState.pointerId !== event.pointerId) {
      return;
    }

    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    if (dragState.didDrag) {
      setPosition((prev) => {
        const element = fabRef.current;
        const clamped = element ? clampPosition(prev, element.offsetWidth, element.offsetHeight) : prev;
        persistPosition(clamped);
        return clamped;
      });
    } else {
      onClick();
    }

    dragStateRef.current = null;
    setIsDragging(false);
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLButtonElement>) => {
    finishDrag(event);
  };

  const handlePointerCancel = (event: React.PointerEvent<HTMLButtonElement>) => {
    finishDrag(event);
  };

  return (
    <Fab
      ref={fabRef}
      variant="extended"
      color="secondary"
      aria-label="Resume tour"
      title="Drag to reposition"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerCancel}
      sx={{
        position: "fixed",
        left: position.left,
        bottom: position.bottom,
        zIndex: 1450,
        textTransform: "none",
        boxShadow: `0 8px 20px ${theme.palette.secondary.main}55`,
        fontWeight: 600,
        cursor: isDragging ? "grabbing" : "grab",
        touchAction: "none",
        userSelect: "none",
      }}
    >
      <HelpOutlineIcon sx={{ mr: 1, fontSize: 18 }} />
      Resume tour
    </Fab>
  );
}
