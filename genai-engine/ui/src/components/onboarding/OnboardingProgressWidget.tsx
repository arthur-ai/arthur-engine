import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import RemoveCircleOutlineIcon from "@mui/icons-material/RemoveCircleOutline";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import Box from "@mui/material/Box";
import Collapse from "@mui/material/Collapse";
import Fab from "@mui/material/Fab";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import { useTheme } from "@mui/material/styles";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useMemo, useState } from "react";

import { runStepAction } from "./hooks/useStepAction";
import { resolveStepTarget, STEPS } from "./steps";
import { useOnboardingStore } from "./stores/onboarding.store";
import { waitForSelectorInDom } from "./utils/waitForSelector";

export const OnboardingProgressWidget = () => {
  const theme = useTheme();
  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const completedSteps = useOnboardingStore((s) => s.completedSteps);
  const skippedSteps = useOnboardingStore((s) => s.skippedSteps);
  const dismiss = useOnboardingStore((s) => s.dismiss);
  const restart = useOnboardingStore((s) => s.restart);
  const reset = useOnboardingStore((s) => s.reset);
  const goTo = useOnboardingStore((s) => s.goTo);
  const [collapsed, setCollapsed] = useState(false);

  const widgetZIndex = theme.zIndex.modal + 11;

  // Skipped counts as moved-past for the purposes of the progress bar.
  const finishedCount = useMemo(() => new Set([...completedSteps, ...skippedSteps]).size, [completedSteps, skippedSteps]);

  // Replay each prereq's action so the UI is in the state the target step expects
  const handleClickStep = async (index: number) => {
    const step = STEPS[index];
    const prereqs = step.prerequisites ?? [];

    if (prereqs.length === 0) {
      goTo(index);
      return;
    }

    for (const prereqId of prereqs) {
      const prereqIndex = STEPS.findIndex((s) => s.id === prereqId);
      if (prereqIndex < 0) continue;

      goTo(prereqIndex);
      const found = await waitForSelectorInDom(resolveStepTarget(STEPS[prereqIndex].target));
      if (!found) return;
      runStepAction(prereqId);
      // Let React flush the action's state mutations before the next prereq runs.
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
  };

  if (status === "idle") return null;

  if (status === "dismissed" || status === "completed") {
    const isCompleted = status === "completed";
    return (
      <Tooltip title={isCompleted ? "Replay walkthrough" : "Resume walkthrough"}>
        <Fab
          size="medium"
          color="primary"
          onClick={isCompleted ? reset : restart}
          sx={{
            position: "fixed",
            bottom: 24,
            left: 24,
            zIndex: widgetZIndex,
          }}
          aria-label="Open onboarding walkthrough"
        >
          <HelpOutlineIcon />
        </Fab>
      </Tooltip>
    );
  }

  const progress = (finishedCount / STEPS.length) * 100;

  return (
    <Paper
      elevation={8}
      sx={{
        position: "fixed",
        bottom: 24,
        left: 24,
        width: 320,
        maxWidth: "calc(100vw - 32px)",
        zIndex: widgetZIndex,
        borderRadius: 2,
        overflow: "hidden",
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          px: 2,
          py: 1.25,
          bgcolor: "primary.main",
          color: "primary.contrastText",
        }}
      >
        <Box>
          <Typography variant="subtitle2" fontWeight={600}>
            Get started with Arthur
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.9 }}>
            {finishedCount} of {STEPS.length} done
          </Typography>
        </Box>
        <Box>
          <Tooltip title="Reset progress">
            <IconButton size="small" onClick={reset} aria-label="Reset walkthrough progress" sx={{ color: "primary.contrastText" }}>
              <RestartAltIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <IconButton
            size="small"
            onClick={() => setCollapsed((v) => !v)}
            aria-label={collapsed ? "Expand walkthrough" : "Collapse walkthrough"}
            sx={{ color: "primary.contrastText" }}
          >
            {collapsed ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
          <IconButton size="small" onClick={dismiss} aria-label="Dismiss walkthrough" sx={{ color: "primary.contrastText" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </Stack>

      <LinearProgress variant="determinate" value={progress} />

      <Collapse in={!collapsed}>
        <List dense sx={{ py: 0.5 }}>
          {STEPS.map((step, index) => {
            const isDone = completedSteps.includes(step.id);
            const isSkipped = !isDone && skippedSteps.includes(step.id);
            const isActive = !isDone && !isSkipped && index === currentStep;
            const isFinished = isDone || isSkipped;
            return (
              <ListItem key={step.id} disablePadding sx={{ bgcolor: isActive ? "action.hover" : "transparent" }}>
                <ListItemButton onClick={() => handleClickStep(index)} sx={{ py: 0.75 }}>
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {isDone ? (
                      <CheckCircleIcon fontSize="small" sx={{ color: "success.main" }} />
                    ) : isSkipped ? (
                      <RemoveCircleOutlineIcon fontSize="small" sx={{ color: "text.disabled" }} />
                    ) : (
                      <RadioButtonUncheckedIcon fontSize="small" sx={{ color: isActive ? "primary.main" : "text.disabled" }} />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={step.label}
                    primaryTypographyProps={{
                      variant: "body2",
                      color: isFinished ? "text.secondary" : "text.primary",
                      fontWeight: isActive ? 600 : 400,
                      sx: isFinished ? { textDecoration: "line-through" } : undefined,
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Collapse>
    </Paper>
  );
};
