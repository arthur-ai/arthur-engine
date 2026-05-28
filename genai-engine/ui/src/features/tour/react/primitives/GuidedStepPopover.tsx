import EastIcon from "@mui/icons-material/East";
import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import { useMemo, type ReactNode } from "react";

import type { StepRenderContext } from "../../core/types";
import { useTour } from "../useTour";
import { useTourLayer } from "../useTourLayer";

import { PopoverAnchor } from "./PopoverAnchor";
import { TargetTracker } from "./TargetTracker";

export function GuidedStepPopover() {
  const { state, activeStep, actions, config } = useTour();
  const popoverZ = useTourLayer("popover");

  const content = useMemo<ReactNode | null>(() => {
    if (!activeStep) return null;
    const { step, section, sectionIndex, stepIndex, globalStepIndex, totalSteps } = activeStep;
    if (typeof step.content !== "function") return step.content;
    const ctx: StepRenderContext = {
      tourId: config.id,
      sectionId: section.id,
      stepId: step.id,
      index: { sectionIndex, stepIndex, globalStepIndex, totalSteps },
      actions,
    };
    return step.content(ctx);
  }, [actions, activeStep, config.id]);

  if (state.status !== "step" || !activeStep?.step.popover) return null;

  const { popover } = activeStep.step;

  return (
    <TargetTracker>
      {({ rect }) => {
        if (!rect) return null;
        return (
          <PopoverAnchor rect={rect} placement={popover.placement ?? activeStep.step.placement ?? "bottom"} offset={12} style={{ zIndex: popoverZ }}>
            <Paper
              elevation={8}
              sx={{
                width: 280,
                borderRadius: 2,
                border: 1,
                borderColor: "divider",
                p: 1.5,
              }}
            >
              <Stack spacing={1.25}>
                {typeof content === "string" ? (
                  <Typography variant="body2" sx={{ color: "text.primary", lineHeight: 1.45 }}>
                    {content}
                  </Typography>
                ) : (
                  <Box sx={{ color: "text.primary", fontSize: 13, lineHeight: 1.45 }}>{content}</Box>
                )}
                {popover.showNext ? (
                  <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                    <Button size="small" variant="contained" endIcon={<EastIcon sx={{ fontSize: 14 }} />} onClick={() => void actions.next()}>
                      {popover.nextLabel ?? "Next"}
                    </Button>
                  </Box>
                ) : null}
              </Stack>
            </Paper>
          </PopoverAnchor>
        );
      }}
    </TargetTracker>
  );
}
