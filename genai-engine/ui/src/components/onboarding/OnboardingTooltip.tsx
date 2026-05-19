import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { TooltipRenderProps } from "react-joyride";

import { useOnboardingStore } from "./stores/onboarding.store";

export const OnboardingTooltip = ({ index, size, step, primaryProps, skipProps, tooltipProps, isLastStep }: TooltipRenderProps) => {
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
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
          <Box>
            <Typography variant="overline" color="primary.main" sx={{ fontWeight: 600, lineHeight: 1 }}>
              Step {index + 1} of {size}
            </Typography>
            <Typography variant="h6" color="text.primary" sx={{ mt: 0.5, fontWeight: 600 }}>
              {step.title as string}
            </Typography>
          </Box>
          <IconButton {...skipProps} size="small" aria-label="Dismiss tour" title="Dismiss tour" sx={{ color: "text.secondary", ml: 1, mt: -0.5 }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Stack>

        <Typography variant="body2" color="text.secondary">
          {step.content as string}
        </Typography>

        <Stack direction="row" justifyContent="flex-end" spacing={1} sx={{ pt: 0.5 }}>
          <Button onClick={() => useOnboardingStore.getState().skipToNext()} variant="text" color="inherit" size="small">
            Skip
          </Button>
          <Button {...primaryProps} variant="contained" color="primary" size="small">
            {isLastStep ? "Finish" : "Next"}
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
};
