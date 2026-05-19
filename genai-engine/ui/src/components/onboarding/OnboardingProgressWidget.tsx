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
import Divider from "@mui/material/Divider";
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
import { useNavigate, useParams } from "react-router-dom";

import { runStepAction } from "./hooks/useStepAction";
import { findMajorTaskForStep, findStep, type MajorTask, MAJOR_TASKS, type MajorTaskId, resolveStepTarget, STEPS, type StepId } from "./steps";
import { useOnboardingStore } from "./stores/onboarding.store";
import { waitForSelectorInDom } from "./utils/waitForSelector";

type MajorTaskStatus = "pending" | "active" | "done";

// Default expansion per phase. User toggles flip the default; phase changes naturally drop the toggle.
const DEFAULT_EXPANDED_FOR_STATUS: Record<MajorTaskStatus, boolean> = {
  active: true,
  done: false,
  pending: false,
};

type ToggleKey = `${MajorTaskId}:${MajorTaskStatus}`;
const toggleKey = (taskId: MajorTaskId, status: MajorTaskStatus): ToggleKey => `${taskId}:${status}`;

const computeMajorTaskStatus = (
  task: MajorTask,
  currentStepId: StepId | undefined,
  completedSet: Set<StepId>,
  skippedSet: Set<StepId>
): MajorTaskStatus => {
  const allFinished = task.subtaskIds.every((id) => completedSet.has(id) || skippedSet.has(id));
  if (allFinished) return "done";
  if (currentStepId && task.subtaskIds.includes(currentStepId)) return "active";
  return "pending";
};

const countDoneSubtasks = (task: MajorTask, completedSet: Set<StepId>, skippedSet: Set<StepId>): number =>
  task.subtaskIds.filter((id) => completedSet.has(id) || skippedSet.has(id)).length;

export const OnboardingProgressWidget = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { id: taskId } = useParams<{ id: string }>();
  const status = useOnboardingStore((s) => s.status);
  const currentStep = useOnboardingStore((s) => s.currentStep);
  const completedSteps = useOnboardingStore((s) => s.completedSteps);
  const skippedSteps = useOnboardingStore((s) => s.skippedSteps);
  const panelCollapsed = useOnboardingStore((s) => s.panelCollapsed);
  const setPanelCollapsed = useOnboardingStore((s) => s.setPanelCollapsed);
  const dismiss = useOnboardingStore((s) => s.dismiss);
  const restart = useOnboardingStore((s) => s.restart);
  const reset = useOnboardingStore((s) => s.reset);
  const goTo = useOnboardingStore((s) => s.goTo);

  const widgetZIndex = theme.zIndex.modal + 11;

  const completedSet = useMemo(() => new Set(completedSteps), [completedSteps]);
  const skippedSet = useMemo(() => new Set(skippedSteps), [skippedSteps]);

  const currentStepConfig = STEPS[currentStep];
  const currentMajorTask = currentStepConfig ? findMajorTaskForStep(currentStepConfig.id) : undefined;

  const finishedMajorTaskCount = useMemo(
    () => MAJOR_TASKS.filter((t) => t.subtaskIds.every((id) => completedSet.has(id) || skippedSet.has(id))).length,
    [completedSet, skippedSet]
  );

  const [userToggles, setUserToggles] = useState<Set<ToggleKey>>(new Set());

  const isExpanded = (taskId: MajorTaskId, status: MajorTaskStatus): boolean => {
    const defaultExpanded = DEFAULT_EXPANDED_FOR_STATUS[status];
    return userToggles.has(toggleKey(taskId, status)) ? !defaultExpanded : defaultExpanded;
  };

  const toggleTask = (taskId: MajorTaskId, status: MajorTaskStatus) => {
    const key = toggleKey(taskId, status);
    setUserToggles((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  // Replay each prereq's action so the UI is in the state the target step expects.
  const handleClickSubtask = async (subtaskId: StepId) => {
    const index = STEPS.findIndex((s) => s.id === subtaskId);
    if (index < 0) return;
    const step = STEPS[index];
    const targetMajorTask = findMajorTaskForStep(subtaskId);

    // Out-of-order jump: force-nav so the spotlight target exists. The tour respects
    // advanceOnArrival on natural flow and won't navigate here.
    const currentTaskMajorId = currentStepConfig ? findMajorTaskForStep(currentStepConfig.id)?.id : undefined;
    if (taskId && targetMajorTask && targetMajorTask.id !== currentTaskMajorId && targetMajorTask.entry) {
      const targetHref = targetMajorTask.entry.route(taskId);
      if (window.location.pathname + window.location.search !== targetHref) {
        navigate(targetHref);
      }
    }

    // Clicking a subtask implies the parent should be expanded; drop any stale active-phase
    // toggle from a prior pass that would otherwise keep it collapsed.
    if (targetMajorTask) {
      const staleKey = toggleKey(targetMajorTask.id, "active");
      setUserToggles((prev) => {
        if (!prev.has(staleKey)) return prev;
        const next = new Set(prev);
        next.delete(staleKey);
        return next;
      });
    }

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
      // Yield so the action's state mutations flush before the next prereq runs.
      await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
    }
    goTo(index);
  };

  if (status === "idle") return null;

  if (status === "dismissed" || status === "completed") {
    const isCompleted = status === "completed";
    const handleReplay = () => {
      setUserToggles(new Set());
      reset();
    };
    return (
      <Tooltip title={isCompleted ? "Replay walkthrough" : "Resume walkthrough"}>
        <Fab
          size="medium"
          color="primary"
          onClick={isCompleted ? handleReplay : restart}
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

  const progress = (finishedMajorTaskCount / MAJOR_TASKS.length) * 100;

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
            {finishedMajorTaskCount} of {MAJOR_TASKS.length} tasks done
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
            onClick={() => setPanelCollapsed(!panelCollapsed)}
            aria-label={panelCollapsed ? "Expand walkthrough" : "Collapse walkthrough"}
            sx={{ color: "primary.contrastText" }}
          >
            {panelCollapsed ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </IconButton>
          <IconButton size="small" onClick={dismiss} aria-label="Dismiss walkthrough" sx={{ color: "primary.contrastText" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
      </Stack>

      <LinearProgress variant="determinate" value={progress} />

      {panelCollapsed && currentMajorTask && (
        <Box sx={{ px: 2, py: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", lineHeight: 1.2 }}>
            Now
          </Typography>
          <Typography variant="body2" color="text.primary" sx={{ fontWeight: 500 }}>
            {currentMajorTask.label}
          </Typography>
        </Box>
      )}

      <Collapse in={!panelCollapsed}>
        <List dense sx={{ py: 0.5 }}>
          {MAJOR_TASKS.map((task, taskIdx) => {
            const taskStatus = computeMajorTaskStatus(task, currentStepConfig?.id, completedSet, skippedSet);
            const isActiveTask = taskStatus === "active";
            const isDoneTask = taskStatus === "done";
            const doneCount = countDoneSubtasks(task, completedSet, skippedSet);
            const expanded = isExpanded(task.id, taskStatus);

            return (
              <Box key={task.id}>
                {taskIdx > 0 && <Divider component="li" />}
                <ListItem disablePadding sx={{ bgcolor: isActiveTask ? "action.hover" : "transparent" }}>
                  <ListItemButton onClick={() => toggleTask(task.id, taskStatus)} sx={{ py: 0.75 }}>
                    <ListItemIcon sx={{ minWidth: 36 }}>
                      {isDoneTask ? (
                        <CheckCircleIcon fontSize="small" sx={{ color: "success.main" }} />
                      ) : (
                        <RadioButtonUncheckedIcon fontSize="small" sx={{ color: isActiveTask ? "primary.main" : "text.disabled" }} />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={task.label}
                      primaryTypographyProps={{
                        variant: "body2",
                        color: isDoneTask ? "text.secondary" : "text.primary",
                        fontWeight: isActiveTask ? 600 : 500,
                      }}
                    />
                    <Stack direction="row" alignItems="center" spacing={0.5}>
                      <Typography variant="caption" color="text.secondary">
                        {doneCount}/{task.subtaskIds.length}
                      </Typography>
                      {expanded ? (
                        <ExpandLessIcon fontSize="small" sx={{ color: "text.secondary" }} />
                      ) : (
                        <ExpandMoreIcon fontSize="small" sx={{ color: "text.secondary" }} />
                      )}
                    </Stack>
                  </ListItemButton>
                </ListItem>
                <Collapse in={expanded} unmountOnExit>
                  <List dense disablePadding>
                    {task.subtaskIds.map((subtaskId) => {
                      const subtask = findStep(subtaskId);
                      if (!subtask) return null;
                      const isDone = completedSet.has(subtaskId);
                      const isSkipped = !isDone && skippedSet.has(subtaskId);
                      const isCurrent = currentStepConfig?.id === subtaskId;
                      const isFinished = isDone || isSkipped;

                      return (
                        <ListItem key={subtaskId} disablePadding sx={{ bgcolor: isCurrent ? "action.hover" : "transparent" }}>
                          <ListItemButton onClick={() => handleClickSubtask(subtaskId)} sx={{ py: 0.5, pl: 5 }}>
                            <ListItemIcon sx={{ minWidth: 28 }}>
                              {isDone ? (
                                <CheckCircleIcon sx={{ fontSize: 16, color: "success.main" }} />
                              ) : isSkipped ? (
                                <RemoveCircleOutlineIcon sx={{ fontSize: 16, color: "text.disabled" }} />
                              ) : (
                                <RadioButtonUncheckedIcon sx={{ fontSize: 16, color: isCurrent ? "primary.main" : "text.disabled" }} />
                              )}
                            </ListItemIcon>
                            <ListItemText
                              primary={subtask.title}
                              primaryTypographyProps={{
                                variant: "body2",
                                color: isFinished ? "text.secondary" : "text.primary",
                                fontWeight: isCurrent ? 600 : 400,
                                sx: isFinished ? { textDecoration: "line-through" } : undefined,
                              }}
                            />
                          </ListItemButton>
                        </ListItem>
                      );
                    })}
                  </List>
                </Collapse>
              </Box>
            );
          })}
        </List>
      </Collapse>
    </Paper>
  );
};
