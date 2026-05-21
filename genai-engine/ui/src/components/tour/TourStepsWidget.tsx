import { Collapsible } from "@base-ui/react/collapsible";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import RadioButtonCheckedIcon from "@mui/icons-material/RadioButtonChecked";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import RouteOutlinedIcon from "@mui/icons-material/RouteOutlined";
import {
  Box,
  Fab,
  IconButton,
  LinearProgress,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { useTourProgress, type TourStepProgress } from "@/components/tour/hooks/useTourProgress";
import { useTourStore } from "@/stores/tour.store";

const WIDGET_Z_INDEX = 1250;

function StepStatusIcon({ status }: { status: TourStepProgress["status"] }) {
  if (status === "completed") {
    return <CheckCircleIcon fontSize="small" color="success" />;
  }

  if (status === "current") {
    return <RadioButtonCheckedIcon fontSize="small" color="primary" />;
  }

  return <RadioButtonUncheckedIcon fontSize="small" sx={{ color: "text.disabled" }} />;
}

export function TourStepsWidget() {
  const progress = useTourProgress();
  const setStep = useTourStore((state) => state.actions.setStep);
  const showGuidance = useTourStore((state) => state.actions.showGuidance);
  const guidanceVisible = useTourStore((state) => state.guidanceVisible);
  const [expanded, setExpanded] = useState(true);

  const currentSectionId = progress?.sections.find((section) => section.steps.some((step) => step.status === "current"))?.id;

  const [openSections, setOpenSections] = useState<string[]>([]);

  useEffect(() => {
    if (!progress) {
      return;
    }

    setOpenSections((prev) => {
      const next = new Set(prev);
      for (const section of progress.sections) {
        if (section.steps.some((step) => step.status === "current" || step.status === "upcoming")) {
          next.add(section.id);
        }
      }
      return Array.from(next);
    });
  }, [progress, currentSectionId]);

  const handleSectionOpenChange = useCallback((sectionId: string, open: boolean) => {
    setOpenSections((prev) => {
      if (open) {
        return prev.includes(sectionId) ? prev : [...prev, sectionId];
      }
      return prev.filter((id) => id !== sectionId);
    });
  }, []);

  const handleStepClick = useCallback(
    (step: TourStepProgress) => {
      if (!progress || step.status === "upcoming") {
        return;
      }
      showGuidance();
      setStep(step.id);
    },
    [progress, setStep, showGuidance]
  );

  if (!progress) {
    return null;
  }

  const progressPercent = progress.totalSteps > 0 ? Math.round((progress.completedCount / progress.totalSteps) * 100) : 0;

  return (
    <Box
      sx={{
        position: "fixed",
        bottom: 24,
        left: 24,
        zIndex: WIDGET_Z_INDEX,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: 1.5,
      }}
    >
      {expanded && (
        <Paper
          elevation={8}
          sx={{
            width: 320,
            maxHeight: "min(70vh, 560px)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            borderRadius: 2,
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{
              px: 2,
              py: 1.5,
              borderBottom: 1,
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Stack spacing={0.25} sx={{ minWidth: 0, flex: 1 }}>
              <Typography variant="subtitle2" fontWeight={600} color="text.primary" noWrap>
                {progress.tourTitle}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {progress.completedCount} of {progress.totalSteps} steps
                {!guidanceVisible ? " · guidance hidden" : ""}
              </Typography>
            </Stack>
            <IconButton size="small" onClick={() => setExpanded(false)} aria-label="Collapse tour checklist">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Stack>

          <LinearProgress variant="determinate" value={progressPercent} sx={{ flexShrink: 0 }} />

          <Box sx={{ overflow: "auto", flex: 1, py: 1 }}>
            <Stack spacing={0.5} sx={{ px: 1 }}>
              {progress.sections.map((section) => {
                const isOpen = openSections.includes(section.id);

                return (
                  <Collapsible.Root
                    key={section.id}
                    open={isOpen}
                    onOpenChange={(open) => handleSectionOpenChange(section.id, open)}
                    render={
                      <Paper
                        variant="outlined"
                        sx={{
                          overflow: "hidden",
                          borderColor: section.steps.some((step) => step.status === "current") ? "primary.main" : "divider",
                        }}
                      />
                    }
                  >
                    <Collapsible.Trigger className="group w-full">
                      <Stack
                        direction="row"
                        alignItems="center"
                        spacing={0.5}
                        sx={{
                          px: 1.5,
                          py: 1,
                          width: "100%",
                          cursor: "pointer",
                          "&:hover": { bgcolor: "action.hover" },
                        }}
                      >
                        <KeyboardArrowRightIcon
                          fontSize="small"
                          sx={{
                            color: "text.secondary",
                            transition: "transform 0.15s ease",
                            transform: isOpen ? "rotate(90deg)" : "none",
                          }}
                        />
                        {section.isComplete ? (
                          <CheckCircleIcon fontSize="small" color="success" sx={{ flexShrink: 0 }} />
                        ) : (
                          <RadioButtonUncheckedIcon fontSize="small" sx={{ color: "text.disabled", flexShrink: 0 }} />
                        )}
                        <Typography variant="body2" fontWeight={600} color="text.primary" sx={{ flex: 1, textAlign: "left" }} noWrap>
                          {section.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
                          {section.completedCount}/{section.totalCount}
                        </Typography>
                      </Stack>
                    </Collapsible.Trigger>

                    <Collapsible.Panel>
                      <List dense disablePadding sx={{ pb: 0.5 }}>
                        {section.steps.map((step) => (
                          <ListItemButton
                            key={step.id}
                            selected={step.status === "current"}
                            disabled={step.status === "upcoming"}
                            onClick={() => handleStepClick(step)}
                            sx={{
                              py: 0.75,
                              pl: 3,
                              pr: 1.5,
                              "&.Mui-selected": { bgcolor: "primary.50" },
                              "&.Mui-disabled": { opacity: 0.55 },
                            }}
                          >
                            <ListItemIcon sx={{ minWidth: 32 }}>
                              <StepStatusIcon status={step.status} />
                            </ListItemIcon>
                            <ListItemText
                              primary={step.title}
                              primaryTypographyProps={{
                                variant: "body2",
                                fontWeight: step.status === "current" ? 600 : 400,
                                color: step.status === "upcoming" ? "text.disabled" : "text.primary",
                              }}
                            />
                          </ListItemButton>
                        ))}
                      </List>
                    </Collapsible.Panel>
                  </Collapsible.Root>
                );
              })}
            </Stack>
          </Box>
        </Paper>
      )}

      <Tooltip title={expanded ? "Hide tour steps" : "Show tour steps"} placement="right">
        <Fab
          color="primary"
          size="medium"
          onClick={() => setExpanded((prev) => !prev)}
          aria-label={expanded ? "Hide tour steps" : "Show tour steps"}
          aria-expanded={expanded}
          sx={{ alignSelf: "flex-start" }}
        >
          <RouteOutlinedIcon />
        </Fab>
      </Tooltip>
    </Box>
  );
}
