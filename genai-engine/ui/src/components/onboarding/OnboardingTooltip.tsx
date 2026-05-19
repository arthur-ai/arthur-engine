import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import type { TooltipRenderProps } from "react-joyride";

import { findMajorTaskForStep, STEPS } from "./steps";
import { useOnboardingStore } from "./stores/onboarding.store";

export const OnboardingTooltip = ({ index, step, primaryProps, skipProps, tooltipProps, isLastStep }: TooltipRenderProps) => {
  const currentSubtask = STEPS[index];
  const majorTask = currentSubtask ? findMajorTaskForStep(currentSubtask.id) : undefined;
  const subtaskPositionInTask = majorTask && currentSubtask ? majorTask.subtaskIds.indexOf(currentSubtask.id) + 1 : index + 1;
  const subtaskCountInTask = majorTask?.subtaskIds.length ?? STEPS.length;
  const sectionName = majorTask?.sectionName ?? "";

  return (
    <Paper
      elevation={8}
      {...tooltipProps}
      sx={{
        width: 360,
        maxWidth: "calc(100vw - 32px)",
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <Stack sx={{ p: 2.5 }} spacing={1.5}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
          <Stack direction="row" alignItems="center" spacing={1}>
            {sectionName && <Chip label={sectionName} size="small" color="primary" variant="outlined" sx={{ fontWeight: 600, height: 22 }} />}
            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 500 }}>
              {subtaskPositionInTask} of {subtaskCountInTask}
            </Typography>
          </Stack>
          <IconButton {...skipProps} size="small" aria-label="Dismiss tour" title="Dismiss tour" sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Stack>

        <Box>
          <Typography variant="h6" color="text.primary" sx={{ fontWeight: 600 }}>
            {step.title as string}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {step.content as string}
          </Typography>
        </Box>

        <Stack direction="row" justifyContent="flex-end" spacing={1} sx={{ pt: 0.5 }}>
          <Tooltip title={sectionName ? `Skip the rest of ${sectionName}` : "Skip this section"}>
            <Button onClick={() => useOnboardingStore.getState().skipToNext()} variant="text" color="inherit" size="small">
              Skip section
            </Button>
          </Tooltip>
          <Button {...primaryProps} variant="contained" color="primary" size="small">
            {isLastStep ? "Finish" : "Next"}
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
};
