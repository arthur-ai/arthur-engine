import { Box, useTheme } from "@mui/material";

export interface PulsingRingProps {
  rect: DOMRect | null;
  padding?: number;
  radius?: number;
  zIndex?: number;
}

/**
 * A fixed-position purple ring drawn around `rect` with an outward pulsing
 * shadow. Sits above the spotlight backdrop and below the popover. Pointer
 * events disabled so clicks fall through to the underlying target.
 */
export function PulsingRing({ rect, padding = 6, radius = 12, zIndex = 1499 }: PulsingRingProps) {
  const theme = useTheme();
  if (!rect) return null;

  const top = rect.top - padding;
  const left = rect.left - padding;
  const width = rect.width + padding * 2;
  const height = rect.height + padding * 2;

  return (
    <Box
      aria-hidden
      sx={{
        position: "fixed",
        top,
        left,
        width,
        height,
        borderRadius: `${radius}px`,
        pointerEvents: "none",
        zIndex,
        transition: "top 0.25s ease, left 0.25s ease, width 0.25s ease, height 0.25s ease",
        boxShadow: `0 0 0 2px ${theme.palette.secondary.main}`,
        "&::after": {
          content: '""',
          position: "absolute",
          inset: 0,
          borderRadius: "inherit",
          border: `2px solid ${theme.palette.secondary.main}`,
          animation: "taskTourPulse 1.6s ease-out infinite",
        },
        "@keyframes taskTourPulse": {
          "0%": { transform: "scale(1)", opacity: 0.85 },
          "70%": { transform: "scale(1.12)", opacity: 0 },
          "100%": { transform: "scale(1.12)", opacity: 0 },
        },
      }}
    />
  );
}
