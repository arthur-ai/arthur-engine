import { Box } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { motion, useReducedMotion } from "framer-motion";

import type { AuroraBlob } from "./types";

export const BackgroundAurora: React.FC = () => {
  const reduceMotion = useReducedMotion();
  const theme = useTheme();

  const blobs: AuroraBlob[] = [
    {
      top: "5%",
      left: "10%",
      size: 600,
      color: alpha(theme.palette.primary.main, 0.18),
      x: [0, 80, -40, 0],
      y: [0, -60, 40, 0],
      duration: 22,
    },
    {
      top: "55%",
      left: "55%",
      size: 700,
      color: alpha(theme.palette.primary.light, 0.16),
      x: [0, -100, 60, 0],
      y: [0, 50, -50, 0],
      duration: 28,
    },
    {
      top: "30%",
      left: "40%",
      size: 500,
      color: alpha(theme.palette.secondary.main, 0.12),
      x: [0, 60, -80, 0],
      y: [0, -40, 60, 0],
      duration: 25,
    },
  ];

  return (
    <Box
      aria-hidden
      sx={{
        position: "absolute",
        inset: 0,
        zIndex: 0,
        overflow: "hidden",
        pointerEvents: "none",
      }}
    >
      {blobs.map((blob, i) => (
        <motion.div
          key={i}
          animate={reduceMotion ? undefined : { x: blob.x, y: blob.y }}
          transition={reduceMotion ? undefined : { duration: blob.duration, repeat: Infinity, ease: "easeInOut" }}
          style={{
            position: "absolute",
            top: blob.top,
            left: blob.left,
            width: blob.size,
            height: blob.size,
            borderRadius: "50%",
            background: `radial-gradient(circle, ${blob.color}, transparent 60%)`,
          }}
        />
      ))}
    </Box>
  );
};
