import { Box } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";

export const BackgroundGrid: React.FC = () => {
  const theme = useTheme();
  const lineColor = alpha(theme.palette.text.primary, 0.06);
  const mask = "radial-gradient(ellipse 60% 50% at center, black 0%, transparent 75%)";
  return (
    <Box
      aria-hidden
      sx={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        backgroundImage: `linear-gradient(to right, ${lineColor} 1px, transparent 1px), linear-gradient(to bottom, ${lineColor} 1px, transparent 1px)`,
        backgroundSize: "44px 44px",
        WebkitMaskImage: mask,
        maskImage: mask,
      }}
    />
  );
};
