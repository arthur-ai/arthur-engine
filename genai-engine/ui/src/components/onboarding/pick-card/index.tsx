import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { Box, Card, CardActionArea, Chip, Stack, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { motion, useReducedMotion, useSpring, useTransform } from "framer-motion";

import { usePointerTracking } from "../use-pointer-tracking";

import type { PickCardProps } from "./types";

const MotionCard = motion.create(Card);

export const PickCard: React.FC<PickCardProps> = ({ variant, icon, badge, title, description, cta, onClick }) => {
  const isPrimary = variant === "primary";
  const reduceMotion = useReducedMotion();
  const theme = useTheme();

  const { ref: cardRef, pointerX, pointerY, handleMouseMove, handleMouseLeave } = usePointerTracking<HTMLDivElement>();
  const rotateX = useTransform(pointerY, [0, 1], [3, -3]);
  const rotateY = useTransform(pointerX, [0, 1], [-3, 3]);
  const springConfig = { damping: 22, stiffness: 240, mass: 0.4 };
  const rotateXSpring = useSpring(rotateX, springConfig);
  const rotateYSpring = useSpring(rotateY, springConfig);

  const liftShadow = isPrimary
    ? `0 8px 24px -10px ${alpha(theme.palette.primary.main, 0.35)}`
    : `0 8px 24px -12px ${alpha(theme.palette.common.black, 0.2)}`;
  const borderGlow = isPrimary ? alpha(theme.palette.primary.main, 0.9) : alpha(theme.palette.text.primary, 0.45);
  const transition = { duration: 0.2, ease: "easeOut" as const };

  return (
    <MotionCard
      ref={cardRef}
      onMouseMove={reduceMotion ? undefined : handleMouseMove}
      onMouseLeave={reduceMotion ? undefined : handleMouseLeave}
      variant="outlined"
      initial="rest"
      animate="rest"
      whileHover={reduceMotion ? undefined : "hover"}
      variants={{
        rest: { y: 0, boxShadow: "0 0 0 0 rgba(0,0,0,0)" },
        hover: { y: -1, boxShadow: liftShadow },
      }}
      transition={transition}
      style={{
        rotateX: reduceMotion ? 0 : rotateXSpring,
        rotateY: reduceMotion ? 0 : rotateYSpring,
        transformPerspective: 1000,
      }}
      sx={(theme) => ({
        position: "relative",
        borderRadius: "12px",
        borderColor: isPrimary ? alpha(theme.palette.primary.main, 0.2) : "divider",
        background: isPrimary
          ? `linear-gradient(180deg, ${alpha(theme.palette.primary.main, 0.06)} 0%, ${theme.palette.background.paper} 60%)`
          : theme.palette.background.paper,
      })}
    >
      <motion.div
        aria-hidden
        variants={{ rest: { opacity: 0 }, hover: { opacity: 1 } }}
        transition={transition}
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "inherit",
          padding: "1px",
          background: `radial-gradient(260px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), ${borderGlow}, transparent 75%)`,
          WebkitMask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
          WebkitMaskComposite: "xor",
          maskComposite: "exclude",
          pointerEvents: "none",
        }}
      />
      {isPrimary && (
        <motion.div
          aria-hidden
          variants={{ rest: { opacity: 0 }, hover: { opacity: 1 } }}
          transition={transition}
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "inherit",
            background: `radial-gradient(380px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), ${alpha(theme.palette.primary.main, 0.22)}, transparent 60%)`,
            pointerEvents: "none",
          }}
        />
      )}
      <CardActionArea
        onClick={onClick}
        sx={{
          position: "relative",
          zIndex: 1,
          p: 3,
          minHeight: 220,
          display: "flex",
          flexDirection: "column",
          alignItems: "stretch",
          justifyContent: "flex-start",
          textAlign: "left",
          gap: 1.5,
          "& .MuiCardActionArea-focusHighlight": { background: "transparent" },
        }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ width: "100%" }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: "8px",
              display: "grid",
              placeItems: "center",
              backgroundColor: isPrimary ? "primary.50" : "action.hover",
              color: isPrimary ? "primary.dark" : "text.secondary",
            }}
          >
            {icon}
          </Box>
          {badge && (
            <Chip
              size="small"
              label={badge}
              sx={{
                height: "auto",
                py: 0.5,
                fontSize: 11,
                fontWeight: 600,
                color: "primary.dark",
                backgroundColor: "primary.50",
                letterSpacing: "0.01em",
                "& .MuiChip-label": { px: 1 },
              }}
            />
          )}
        </Stack>

        <Typography
          sx={{
            fontSize: 17,
            fontWeight: 600,
            color: "text.primary",
            letterSpacing: "-0.01em",
            mt: 0.5,
          }}
        >
          {title}
        </Typography>

        <Typography
          sx={{
            fontSize: 13,
            color: "text.secondary",
            lineHeight: 1.5,
            flex: 1,
          }}
        >
          {description}
        </Typography>

        <Stack
          direction="row"
          alignItems="center"
          spacing={0.75}
          sx={{
            fontSize: 13,
            fontWeight: 600,
            color: isPrimary ? "primary.dark" : "text.primary",
            mt: 0.5,
          }}
        >
          <Typography component="span" sx={{ fontSize: 13, fontWeight: 600, color: "inherit" }}>
            {cta}
          </Typography>
          <motion.span
            variants={{ rest: { x: 0 }, hover: { x: 2 } }}
            transition={transition}
            style={{ display: "inline-flex", alignItems: "center" }}
          >
            <ArrowForwardIcon sx={{ fontSize: 14 }} />
          </motion.span>
        </Stack>
      </CardActionArea>
    </MotionCard>
  );
};
