import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckIcon from "@mui/icons-material/Check";
import { Box, Button, Stack, Typography } from "@mui/material";

import { EngineTopNav } from "./EngineTopNav";

const BRAND_PURPLE = "#7C3AED";
const METRIC_SUCCESS = "#10B981";

interface LandingHeroProps {
  onTry: () => void;
  onLogin: () => void;
}

export const LandingHero: React.FC<LandingHeroProps> = ({ onTry, onLogin }) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      minHeight: "100vh",
      background: "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(124,58,237,0.06), transparent 60%), #F9FAFB",
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
      <Box sx={{ width: "100%", maxWidth: 640 }}>
        {/* Pill */}
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{
            display: "inline-flex",
            fontSize: 12,
            fontWeight: 600,
            color: BRAND_PURPLE,
            backgroundColor: "rgba(124,58,237,0.08)",
            px: 1.5,
            py: 0.75,
            borderRadius: "999px",
            mb: 2.5,
          }}
        >
          <Box
            sx={{
              width: 6,
              height: 6,
              borderRadius: "999px",
              backgroundColor: BRAND_PURPLE,
              boxShadow: "0 0 0 4px rgba(124,58,237,0.15)",
            }}
          />
          <Typography component="span" sx={{ fontSize: 12, fontWeight: 600, color: "inherit" }}>
            Live demo · 30s setup
          </Typography>
        </Stack>

        {/* Headline */}
        <Typography
          component="h1"
          sx={{
            fontSize: 30,
            fontWeight: 700,
            color: "text.primary",
            letterSpacing: "-0.02em",
            lineHeight: 1.15,
            mb: 1.5,
            textWrap: "balance",
          }}
        >
          See your agent&apos;s traces, tokens &amp; evals in real time.
        </Typography>

        {/* Lede */}
        <Typography
          sx={{
            fontSize: 15,
            color: "text.secondary",
            lineHeight: 1.55,
            mb: 3.5,
            textWrap: "pretty",
          }}
        >
          The fastest way to see what Arthur Engine does — a working task, populated with a demo agent, waiting for you.
        </Typography>

        {/* Hero actions */}
        <Stack direction="row" alignItems="center" spacing={1.75} sx={{ mt: 1, mb: 4, flexWrap: "wrap" }}>
          <Button
            variant="contained"
            disableElevation
            onClick={onTry}
            endIcon={<ArrowForwardIcon sx={{ fontSize: 16 }} />}
            sx={{
              backgroundColor: "#2563EB",
              color: "common.white",
              textTransform: "none",
              fontSize: 15,
              fontWeight: 600,
              borderRadius: "8px",
              px: 2.75,
              py: 1.5,
              "&:hover": { backgroundColor: "#1D4ED8" },
            }}
          >
            Try it out right now
          </Button>
          <Typography component="span" sx={{ fontSize: 13, color: "grey.400" }}>
            or
          </Typography>
          <Button
            variant="outlined"
            onClick={onLogin}
            sx={{
              textTransform: "none",
              fontSize: 14,
              fontWeight: 600,
              borderRadius: "8px",
              borderColor: "grey.300",
              color: "text.primary",
              backgroundColor: "transparent",
              px: 2.25,
              py: 1.25,
              "&:hover": { backgroundColor: "grey.50", borderColor: "grey.400" },
            }}
          >
            Sign up for an account
          </Button>
        </Stack>

        {/* Bullets */}
        <Stack component="ul" direction="row" spacing={3} sx={{ flexWrap: "wrap", p: 0, m: 0, listStyle: "none" }}>
          {["Pre-loaded demo agent", "Task-scoped API key", "No card, no signup"].map((text) => (
            <Stack key={text} component="li" direction="row" alignItems="center" spacing={1} sx={{ fontSize: 13, color: "text.secondary" }}>
              <CheckIcon sx={{ fontSize: 14, color: METRIC_SUCCESS }} />
              <Typography component="span" sx={{ fontSize: 13, color: "inherit" }}>
                {text}
              </Typography>
            </Stack>
          ))}
        </Stack>
      </Box>
    </Box>
  </Box>
);
