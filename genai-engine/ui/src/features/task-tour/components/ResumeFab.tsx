import TourOutlinedIcon from "@mui/icons-material/TourOutlined";
import { Box, Fab, Stack, Tooltip, Typography, useTheme } from "@mui/material";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

import { TASK_TOUR_SHORT_NAME } from "../data";

export interface ResumeFabProps {
  /** Current step title shown on the button face. */
  label: string;
  /** Short tour name shown above the step title. */
  tourName?: string;
  /** When true, gently pulses to draw attention (e.g. while the tour is dismissed). */
  attractAttention?: boolean;
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
export function ResumeFab({ label, tourName = TASK_TOUR_SHORT_NAME, attractAttention = false, onClick, onAnchorRectChange }: ResumeFabProps) {
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
    [persistPosition]
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

  const tooltip = `Open ${tourName} guided tour — ${label}. Click to continue, drag to reposition.`;
  const ariaLabel = `Open ${tourName} guided tour: ${label}`;

  return (
    <Tooltip title={tooltip} placement="top" enterDelay={400} disableHoverListener={isDragging}>
      <Fab
        ref={fabRef}
        variant="extended"
        color="secondary"
        aria-label={ariaLabel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        sx={{
          position: "fixed",
          left: position.left,
          bottom: position.bottom,
          zIndex: 1450,
          px: 1.5,
          py: 1.25,
          height: "auto",
          minHeight: 48,
          textTransform: "none",
          boxShadow: `0 8px 20px ${theme.palette.secondary.main}55`,
          color: "text.primary",
          cursor: isDragging ? "grabbing" : "grab",
          touchAction: "none",
          userSelect: "none",
          "&:hover": {
            color: "text.primary",
          },
          ...(attractAttention
            ? {
                "@keyframes tourFabPulse": {
                  "0%, 100%": {
                    boxShadow: `0 8px 20px ${theme.palette.secondary.main}55`,
                  },
                  "50%": {
                    boxShadow: `0 10px 28px ${theme.palette.secondary.main}99`,
                  },
                },
                animation: "tourFabPulse 2.5s ease-in-out infinite",
                "@media (prefers-reduced-motion: reduce)": {
                  animation: "none",
                },
              }
            : {}),
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1.25} sx={{ minWidth: 0 }}>
          <Box
            aria-hidden
            sx={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 28,
              height: 28,
              borderRadius: "50%",
              flexShrink: 0,
              bgcolor: "secondary.dark",
              color: "common.white",
            }}
          >
            <TourOutlinedIcon sx={{ fontSize: 16 }} />
          </Box>

          <Stack spacing={0.125} sx={{ minWidth: 0, textAlign: "left" }}>
            <Typography
              variant="caption"
              sx={{
                lineHeight: 1.2,
                fontWeight: 600,
                letterSpacing: 0.2,
                color: "text.secondary",
              }}
            >
              {tourName} · Guided tour
            </Typography>
            <Typography
              component="span"
              variant="body2"
              sx={{
                lineHeight: 1.25,
                fontWeight: 600,
                color: "text.primary",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                maxWidth: 220,
              }}
            >
              {label}
            </Typography>
          </Stack>
        </Stack>
      </Fab>
    </Tooltip>
  );
}
