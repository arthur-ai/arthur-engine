import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import VpnKeyOutlinedIcon from "@mui/icons-material/VpnKeyOutlined";
import { Box, Card, CardActionArea, Chip, Link, Stack, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { motion, useReducedMotion, useSpring, useTransform } from "framer-motion";

import { EngineTopNav } from "./EngineTopNav";
import { usePointerTracking } from "./usePointerTracking";

interface LandingHeroProps {
  onTry: () => void;
  onLogin: () => void;
}

export const LandingHero: React.FC<LandingHeroProps> = ({ onTry, onLogin }) => (
  <Box
    sx={{
      position: "relative",
      backgroundColor: "background.default",
      overflow: "hidden",
    }}
  >
    <BackgroundGrid />
    <BackgroundAurora />
    <Box
      sx={{
        position: "relative",
        zIndex: 1,
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
      }}
    >
      <EngineTopNav />
      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "safe center",
          justifyContent: "safe center",
          px: 3,
          py: 4,
          overflowY: "auto",
        }}
      >
        <Box sx={{ width: "100%", maxWidth: 880 }}>
          <Typography
            component="div"
            sx={{
              fontSize: 12,
              fontWeight: 600,
              color: "secondary.main",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              mb: 1.5,
            }}
          >
            Welcome
          </Typography>

          <Typography
            component="h1"
            sx={{
              fontSize: 32,
              fontWeight: 700,
              color: "text.primary",
              letterSpacing: "-0.02em",
              lineHeight: 1.15,
              mb: 1.5,
              textWrap: "balance",
            }}
          >
            Get started with Arthur Engine
          </Typography>

          <Typography
            sx={{
              fontSize: 15,
              color: "text.secondary",
              lineHeight: 1.55,
              mb: 3.5,
              textWrap: "pretty",
            }}
          >
            Observability, evals, and guardrails for production LLM agents. Pick a path below.
          </Typography>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
              gap: 2,
              mt: 1,
            }}
          >
            <PickCard
              variant="primary"
              icon={<BoltOutlinedIcon sx={{ fontSize: 18 }} />}
              badge="No account needed"
              title="Try it out right now"
              description="Spin up a sandbox task pre-loaded with a demo agent. You'll be in the engine in under 30 seconds."
              cta="Start the demo"
              onClick={onTry}
            />
            <PickCard
              variant="default"
              icon={<VpnKeyOutlinedIcon sx={{ fontSize: 18 }} />}
              title="Sign up for an account"
              description="Full Arthur platform access — your own workspace, persistent tasks, and team collaboration."
              cta="Continue to sign in"
              onClick={onLogin}
            />
          </Box>

          <Typography
            component="div"
            sx={{
              mt: 3.5,
              textAlign: "center",
              fontSize: 12,
              color: "text.disabled",
            }}
          >
            By continuing you agree to Arthur&apos;s{" "}
            <Link href="#" underline="always" sx={{ color: "text.secondary", fontWeight: 500 }}>
              Terms
            </Link>{" "}
            and{" "}
            <Link href="#" underline="always" sx={{ color: "text.secondary", fontWeight: 500 }}>
              Privacy Policy
            </Link>
            .
          </Typography>
        </Box>
      </Box>
    </Box>
  </Box>
);

const BackgroundGrid: React.FC = () => {
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

interface AuroraBlob {
  top: string;
  left: string;
  size: number;
  color: string;
  x: number[];
  y: number[];
  duration: number;
}

const BackgroundAurora: React.FC = () => {
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

interface PickCardProps {
  variant: "primary" | "default";
  icon: React.ReactNode;
  badge?: string;
  title: string;
  description: string;
  cta: string;
  onClick: () => void;
}

const MotionCard = motion.create(Card);

const PickCard: React.FC<PickCardProps> = ({ variant, icon, badge, title, description, cta, onClick }) => {
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
