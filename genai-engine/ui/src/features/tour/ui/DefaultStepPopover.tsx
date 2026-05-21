import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import { useMemo } from "react";

import type { StepRenderContext, TourActions } from "../core/types";
import { useTourEngine, type ActiveStep } from "../react/useTour";

export interface DefaultStepPopoverProps {
  activeStep: ActiveStep;
  actions: TourActions;
}

/**
 * Default popover body rendered inside `PopoverAnchor`. Composes section title,
 * progress, step content, and the standard Skip / Back / Next-Done controls.
 *
 * Step content may be a `ReactNode` or a function receiving a
 * `StepRenderContext`; both are supported here.
 */
export function DefaultStepPopover({ activeStep, actions }: DefaultStepPopoverProps) {
  const engine = useTourEngine();
  const { section, step, globalStepIndex, totalSteps, stepIndex, sectionIndex } = activeStep;

  const isFirstStep = globalStepIndex === 0;
  const isLastStep = globalStepIndex === totalSteps - 1;
  const skipable = section.skipable !== false;

  const renderedContent = useMemo(() => {
    if (typeof step.content !== "function") return step.content;
    const ctx: StepRenderContext = {
      tourId: engine.config.id,
      sectionId: section.id,
      stepId: step.id,
      index: {
        sectionIndex,
        stepIndex,
        globalStepIndex,
        totalSteps,
      },
      actions,
    };
    return step.content(ctx);
  }, [step, section.id, sectionIndex, stepIndex, globalStepIndex, totalSteps, actions, engine.config.id]);

  return (
    <Paper elevation={8} sx={{ p: 2, maxWidth: 360, borderRadius: 2, bgcolor: "background.paper" }}>
      <Stack spacing={1.5}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
          {section.title ? (
            <Typography variant="subtitle2" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
              {section.title}
            </Typography>
          ) : (
            <Box />
          )}
          <Typography variant="caption" color="text.secondary">
            Step {globalStepIndex + 1} of {totalSteps}
          </Typography>
        </Stack>

        <Box sx={{ color: "text.primary" }}>
          {typeof renderedContent === "string" ? <Typography variant="body2">{renderedContent}</Typography> : renderedContent}
        </Box>

        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1} sx={{ pt: 0.5 }}>
          {skipable ? (
            <Button onClick={() => actions.skip()} variant="text" color="inherit" size="small">
              Skip
            </Button>
          ) : (
            <Box />
          )}
          <Stack direction="row" spacing={1}>
            <Button onClick={() => actions.prev()} variant="outlined" size="small" disabled={isFirstStep}>
              Back
            </Button>
            <Button onClick={() => actions.next()} variant="contained" color="primary" size="small">
              {isLastStep ? "Done" : "Next"}
            </Button>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  );
}
