import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import EastIcon from "@mui/icons-material/East";
import { Box, Button, IconButton, Paper, Stack, Tooltip, Typography } from "@mui/material";
import { useCallback } from "react";

import { TASK_TOUR_SECTIONS } from "../data";

import { useTour } from "@/features/tour";

const PANEL_WIDTH = 320;
const PANEL_Z_INDEX = 1450;

export function SectionCompleteWidget() {
  const { state, actions } = useTour();
  const handleContinue = useCallback(() => actions.continueFromSectionComplete(), [actions]);
  const handleDismiss = useCallback(() => actions.dismiss(), [actions]);

  if (state.status !== "sectionComplete") return null;

  const section = TASK_TOUR_SECTIONS[state.sectionIndex];
  const nextSection = state.nextSectionIndex === undefined ? undefined : TASK_TOUR_SECTIONS[state.nextSectionIndex];
  if (!section) return null;

  return (
    <Paper
      elevation={8}
      sx={{
        width: PANEL_WIDTH,
        borderRadius: 2.5,
        border: 1,
        borderColor: "divider",
        overflow: "hidden",
        zIndex: PANEL_Z_INDEX,
        position: "fixed",
        bottom: 20,
        right: 20,
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ p: 1.75, borderBottom: 1, borderColor: "divider" }}>
        <CheckCircleIcon sx={{ color: "success.main", fontSize: 20 }} />
        <Typography variant="body2" sx={{ fontWeight: 600, flex: 1, minWidth: 0 }}>
          Section complete
        </Typography>
        <Tooltip title="Hide walkthrough">
          <IconButton size="small" onClick={handleDismiss} sx={{ color: "text.disabled" }}>
            <CloseIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
      </Stack>

      <Box sx={{ p: 2 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.primary", mb: 0.75 }}>
          {section.title}
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", lineHeight: 1.5 }}>
          Take a moment to review the result. Continue when you are ready for{" "}
          {nextSection ? `the next section, ${nextSection.title}.` : "the completion summary."}
        </Typography>
      </Box>

      <Stack direction="row" justifyContent="flex-end" sx={{ px: 2, pb: 2 }}>
        <Button variant="contained" color="primary" onClick={handleContinue} endIcon={<EastIcon sx={{ fontSize: 16 }} />}>
          {nextSection ? "Continue" : "Finish tour"}
        </Button>
      </Stack>
    </Paper>
  );
}
