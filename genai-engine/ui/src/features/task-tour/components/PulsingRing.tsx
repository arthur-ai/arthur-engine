import { Box, useTheme } from "@mui/material";

export interface PulsingRingProps {
  rect: DOMRect | null;
  padding?: number;
  radius?: number;
  zIndex?: number;
}

function getPulseExpansionGeometry(radius: number, spread: number): { inset: number; radius: number } {
  return {
    inset: -spread,
    radius: radius + spread,
  };
}

/**
 * A fixed-position purple ring drawn around `rect` with an outward pulsing
 * shadow. Sits above the spotlight backdrop and below the popover. Pointer
 * events disabled so clicks fall through to the underlying target.
 */
export function PulsingRing({ rect, padding = 6, radius = 12, zIndex = 1499 }: PulsingRingProps) {
  const theme = useTheme();
  if (!rect) return null;

  const pulseSpread = 16;
  const top = rect.top - padding;
  const left = rect.left - padding;
  const width = rect.width + padding * 2;
  const height = rect.height + padding * 2;
  const pulseGeometry = getPulseExpansionGeometry(radius, pulseSpread);

  return (
    <Box
      aria-hidden
      sx={{
        position: "fixed",
        top,
        left,
        width,
        height,
        "--task-tour-pulse-inset": `${pulseGeometry.inset}px`,
        "--task-tour-pulse-radius": `${pulseGeometry.radius}px`,
        borderRadius: `${radius}px`,
        pointerEvents: "none",
        zIndex,
        transition: "top 0.25s ease, left 0.25s ease, width 0.25s ease, height 0.25s ease",
        boxShadow: `0 0 0 2px ${theme.palette.secondary.main}`,
        "&::after": {
          content: '""',
          position: "absolute",
          top: 0,
          right: 0,
          bottom: 0,
          left: 0,
          borderRadius: "inherit",
          border: `2px solid ${theme.palette.secondary.main}`,
          willChange: "top, right, bottom, left, border-radius, opacity",
          animation: "taskTourPulse 1.6s ease-out infinite",
        },
        "@keyframes taskTourPulse": {
          "0%": { top: 0, right: 0, bottom: 0, left: 0, borderRadius: "inherit", opacity: 0 },
          "10%": { top: 0, right: 0, bottom: 0, left: 0, borderRadius: "inherit", opacity: 0.85 },
          "70%": {
            top: "var(--task-tour-pulse-inset)",
            right: "var(--task-tour-pulse-inset)",
            bottom: "var(--task-tour-pulse-inset)",
            left: "var(--task-tour-pulse-inset)",
            borderRadius: "var(--task-tour-pulse-radius)",
            opacity: 0,
          },
          "100%": {
            top: "var(--task-tour-pulse-inset)",
            right: "var(--task-tour-pulse-inset)",
            bottom: "var(--task-tour-pulse-inset)",
            left: "var(--task-tour-pulse-inset)",
            borderRadius: "var(--task-tour-pulse-radius)",
            opacity: 0,
          },
        },
        "@media (prefers-reduced-motion: reduce)": {
          transition: "none",
          "&::after": {
            animation: "none",
          },
        },
      }}
    />
  );
}
