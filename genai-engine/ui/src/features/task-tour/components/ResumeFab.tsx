import TourOutlinedIcon from "@mui/icons-material/TourOutlined";
import { Box, Fab, Stack, Tooltip, Typography, useTheme } from "@mui/material";

import { TASK_TOUR_SHORT_NAME } from "../data";
import { TASK_TOUR_DOCK_STORAGE_KEY, defaultDockPosition } from "../dockPosition";
import { useDraggable } from "../hooks/useDraggable";

export interface ResumeFabProps {
  /** Current step title shown on the button face. */
  label: string;
  /** Short tour name shown above the step title. */
  tourName?: string;
  /** When true, gently pulses to draw attention (e.g. while the tour is dismissed). */
  attractAttention?: boolean;
  onClick: () => void;
}

/**
 * Floating action button that re-opens a dismissed tour. Draggable so users
 * can move it out of the way; its position is shared with the checklist panel
 * (see {@link defaultDockPosition}) so the two stay grouped — dragging either
 * repositions the other. Styled with the same brand-purple accent as the
 * spotlight ring.
 */
export function ResumeFab({ label, tourName = TASK_TOUR_SHORT_NAME, attractAttention = false, onClick }: ResumeFabProps) {
  const theme = useTheme();
  const {
    position,
    isDragging,
    ref: fabRef,
    handleProps,
  } = useDraggable<HTMLButtonElement>({ storageKey: TASK_TOUR_DOCK_STORAGE_KEY, defaultPosition: defaultDockPosition, onClick });

  const tooltip = `Open ${tourName} guided tour — ${label}. Click to continue, drag to reposition.`;
  const ariaLabel = `Open ${tourName} guided tour: ${label}`;

  return (
    <Tooltip title={tooltip} placement="top" enterDelay={400} disableHoverListener={isDragging}>
      <Fab
        ref={fabRef}
        variant="extended"
        color="secondary"
        aria-label={ariaLabel}
        {...handleProps}
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
