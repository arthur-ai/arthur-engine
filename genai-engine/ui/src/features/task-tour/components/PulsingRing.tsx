import { Box, useTheme } from "@mui/material";

export interface PulsingRingProps {
  rect: DOMRect | null;
  padding?: number;
  radius?: number;
  zIndex?: number;
}

export function PulsingRing({ rect, padding = 6, radius = 12, zIndex = 1499 }: PulsingRingProps) {
  const theme = useTheme();
  if (!rect) return null;

  const top = rect.top - padding;
  const left = rect.left - padding;
  const width = rect.width + padding * 2;
  const height = rect.height + padding * 2;

  const spread = 14;
  const scaleX = ((width + spread * 2) / width).toFixed(4);
  const scaleY = ((height + spread * 2) / height).toFixed(4);

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
          transformOrigin: "center",
          willChange: "transform, opacity",
          animation: "taskTourPulse 1.6s ease-out infinite",
        },
        "@keyframes taskTourPulse": {
          "0%": { transform: "scale(1)", opacity: 0.8 },
          "70%": { transform: `scale(${scaleX}, ${scaleY})`, opacity: 0 },
          "100%": { transform: `scale(${scaleX}, ${scaleY})`, opacity: 0 },
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
