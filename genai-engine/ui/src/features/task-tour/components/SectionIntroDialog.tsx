import CloseIcon from "@mui/icons-material/Close";
import EastIcon from "@mui/icons-material/East";
import { Box, Button, Dialog, IconButton, Paper, Stack, Typography, useTheme } from "@mui/material";

import type { TaskTourSection } from "../data";

import { ADLCFlywheel } from "./ADLCFlywheel";

export interface SectionIntroDialogProps {
  open: boolean;
  section: TaskTourSection | null;
  /** Index of this section among all sections (0-based). Determines whether we show the hero flywheel. */
  sectionIndex: number;
  onStart: () => void;
  onDismiss: () => void;
}

/**
 * The section introduction modal. Mirrors the design's two-up layout — hero
 * block for section 0 (with the ADLC flywheel diagram), and a compact
 * heading-only block for subsequent sections.
 */
export function SectionIntroDialog({ open, section, sectionIndex, onStart, onDismiss }: SectionIntroDialogProps) {
  const theme = useTheme();
  if (!section) return null;

  const intro = section.intro;
  const isHero = sectionIndex === 0 || intro.showFlywheel === true;

  return (
    <Dialog
      open={open}
      onClose={onDismiss}
      maxWidth="sm"
      fullWidth
      aria-labelledby="task-tour-section-intro-title"
      slotProps={{
        paper: {
          elevation: 16,
          sx: { borderRadius: 3, overflow: "hidden", position: "relative" },
        },
      }}
    >
      <IconButton
        size="small"
        onClick={onDismiss}
        aria-label="Dismiss tour"
        sx={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 1,
          color: "text.secondary",
          "&:hover": { color: "text.primary", bgcolor: "action.hover" },
        }}
      >
        <CloseIcon sx={{ fontSize: 18 }} />
      </IconButton>

      {isHero ? (
        <Box
          sx={{
            background: `linear-gradient(140deg, ${theme.palette.secondary.light}22 0%, ${theme.palette.secondary.light}44 50%, ${theme.palette.primary.light}33 100%)`,
            px: 4,
            pt: 3.5,
            pb: 0.5,
          }}
        >
          <Typography
            variant="overline"
            sx={{
              display: "block",
              color: "secondary.main",
              letterSpacing: 1,
              fontWeight: 600,
              mb: 1,
              fontSize: 11,
            }}
          >
            {section.kicker}
          </Typography>
          <Typography id="task-tour-section-intro-title" variant="h5" sx={{ fontWeight: 700, letterSpacing: -0.5, mb: 1.5, color: "text.primary" }}>
            {intro.heading}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", lineHeight: 1.55, mb: 1.5 }}>
            {intro.body}
          </Typography>
          <Box sx={{ display: "flex", justifyContent: "center", pb: 1.5 }}>
            <ADLCFlywheel />
          </Box>
        </Box>
      ) : (
        <Box sx={{ px: 4, pt: 3.5, pb: 0.5 }}>
          <Typography variant="overline" sx={{ display: "block", color: "secondary.main", letterSpacing: 1, fontWeight: 600, mb: 1, fontSize: 11 }}>
            {section.kicker}
          </Typography>
          <Typography id="task-tour-section-intro-title" variant="h5" sx={{ fontWeight: 700, letterSpacing: -0.5, mb: 1.5, color: "text.primary" }}>
            {intro.heading}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", lineHeight: 1.55, mb: 1.5 }}>
            {intro.body}
          </Typography>
        </Box>
      )}

      {intro.scenario ? (
        <Paper
          variant="outlined"
          sx={{
            mx: 4,
            my: 0.5,
            mb: 2.25,
            p: 1.75,
            borderStyle: "dashed",
            borderRadius: 2,
            bgcolor: "background.default",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              display: "block",
              color: "secondary.main",
              letterSpacing: 0.5,
              fontWeight: 600,
              textTransform: "uppercase",
              fontSize: 11,
              mb: 0.5,
            }}
          >
            {intro.scenario.label}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary", lineHeight: 1.55 }}>
            {intro.scenario.text}
          </Typography>
        </Paper>
      ) : null}

      <Stack direction="row" alignItems="center" justifyContent="flex-end" spacing={1.5} sx={{ px: 4, pb: 2.75, pt: 0.5 }}>
        <Button variant="outlined" color="inherit" onClick={onDismiss} sx={{ whiteSpace: "nowrap" }}>
          Dismiss tour
        </Button>
        <Button variant="contained" color="primary" onClick={onStart} endIcon={<EastIcon sx={{ fontSize: 16 }} />} sx={{ whiteSpace: "nowrap" }}>
          {intro.cta}
        </Button>
      </Stack>
    </Dialog>
  );
}
