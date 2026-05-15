import BoltOutlinedIcon from "@mui/icons-material/BoltOutlined";
import VpnKeyOutlinedIcon from "@mui/icons-material/VpnKeyOutlined";
import { Box, Link, Typography } from "@mui/material";

import { BackgroundAurora } from "../background-aurora";
import { BackgroundGrid } from "../background-grid";
import { EngineTopNav } from "../engine-top-nav";
import { PickCard } from "../pick-card";

import type { LandingHeroProps } from "./types";

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
              title="Log in with API key"
              description="Full Arthur platform access — your own workspace, persistent tasks, and team collaboration."
              cta="Continue to log in"
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
