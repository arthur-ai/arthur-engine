import { Box, CircularProgress } from "@mui/material";

import { BackgroundAurora } from "../background-aurora";
import { BackgroundGrid } from "../background-grid";
import { EngineTopNav } from "../engine-top-nav";

type OnboardingLayoutProps = {
  variant?: "landing" | "default";
  contentMaxWidth?: number;
  children: React.ReactNode;
};

export const OnboardingLayout: React.FC<OnboardingLayoutProps> = ({ variant = "default", contentMaxWidth = 520, children }) => (
  <Box
    sx={{
      position: "relative",
      backgroundColor: "background.default",
      overflow: "hidden",
      minHeight: "100vh",
    }}
  >
    {variant === "landing" && (
      <>
        <BackgroundGrid />
        <BackgroundAurora />
      </>
    )}
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
        <Box sx={{ width: "100%", maxWidth: contentMaxWidth }}>{children}</Box>
      </Box>
    </Box>
  </Box>
);

export const OnboardingContentFallback: React.FC = () => (
  <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
    <CircularProgress />
  </Box>
);
