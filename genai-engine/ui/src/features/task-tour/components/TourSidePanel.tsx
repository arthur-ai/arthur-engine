import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import TourOutlinedIcon from "@mui/icons-material/TourOutlined";
import { Box, Button, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import { useCallback, useEffect } from "react";

import { TASK_TOUR_SECTIONS, TASK_TOUR_SHORT_NAME } from "../data";
import { useChecklistController } from "../hooks/useChecklistController";
import { getTaskTourStepLabel } from "../tour-config";

import { ChecklistPanelBody } from "./ChecklistPanelBody";

import { useTour, useTourLayer, useTourPluginStore, type TourStatePlugin } from "@/features/tour";
import { useTourPanelStore } from "@/stores/tour-panel.store";

export interface TourSidePanelProps {
  /** Shared state plugin owned by `TaskTour`. */
  statePlugin: TourStatePlugin;
}

const RAIL_WIDTH = 44;
const CONTENT_WIDTH = 312;

/**
 * In-flow, root-level docked panel that hosts the tour's persistent surfaces —
 * the checklist (while a step is active) and the resume card (while dismissed).
 * Unlike the old floating widgets it is a flex sibling of the page `<main>`, so
 * it takes window space away from the app rather than covering it. Collapses to
 * a thin rail via the chevron; the open/closed choice lives in
 * {@link useTourPanelStore}, independent of tour progress.
 */
export function TourSidePanel({ statePlugin }: TourSidePanelProps) {
  const collapsed = useTourPanelStore((s) => s.collapsed);
  const toggle = useTourPanelStore((s) => s.toggle);

  const controller = useChecklistController(statePlugin);
  const persistedStatus = useTourPluginStore(statePlugin, (s) => s.snapshot.status);
  const { state, actions, config } = useTour();
  // The spotlight backdrop/blocker is a viewport-spanning fixed overlay
  // (`blocker` layer ≈ 1401) and would otherwise dim and click-block the
  // docked panel. Lift the panel onto the `panel` layer (≈ 1450) so it stays
  // visible and interactive above the backdrop, while remaining below the
  // step popover (1500) and the certificate dialog (1600).
  const panelLayer = useTourLayer("panel");

  const showResume = persistedStatus === "dismissed";
  // Mounted across the whole active tour (intro → step → sectionComplete) plus
  // the dismissed/resume state, so it never blinks out (and the page never
  // reflows) between sections. Hidden only when idle/completed/skipped.
  const hasContent = controller.isRunning || showResume;

  // Publish the width we reserve on the right so viewport-anchored overlays
  // (MUI dialogs/drawers — see `mui-theme.ts`) can subtract it. 0 when the panel
  // isn't showing; reset to 0 on unmount so nothing stays inset after the tour.
  const reservedWidth = hasContent ? (collapsed ? RAIL_WIDTH : RAIL_WIDTH + CONTENT_WIDTH) : 0;
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--app-inset-right", `${reservedWidth}px`);
    return () => root.style.setProperty("--app-inset-right", "0px");
  }, [reservedWidth]);

  const resumeLabel = (() => {
    if (state.status === "step") return getTaskTourStepLabel(state.sectionId, state.stepId);
    if (state.status === "intro") return getTaskTourStepLabel(state.sectionId, undefined);
    const resume = statePlugin.resumePosition(config);
    return resume ? getTaskTourStepLabel(resume.sectionId, resume.stepId) : "Resume tour";
  })();

  const handleResume = useCallback(() => {
    if (state.status === "dismissed") {
      actions.resume();
      return;
    }
    // Engine is idle or has finished — start fresh at the first incomplete
    // step. If `resumePosition` returns null every step is already complete,
    // so a "resume" would silently loop back to section 0; treat it as a no-op.
    const resumePosition = statePlugin.resumePosition(config);
    if (!resumePosition) return;
    actions.start({ position: resumePosition, resume: true });
  }, [actions, config, state, statePlugin]);

  // Nothing to show (idle / completed): the panel claims no layout space.
  if (!hasContent) return null;

  const progressPct = Math.min(100, Math.max(0, controller.totalProgress * 100));

  return (
    <Box
      component="aside"
      sx={{
        display: "flex",
        height: "100%",
        flexShrink: 0,
        overflow: "hidden",
        // `relative` so `zIndex` applies to this in-flow flex child. Lift it
        // above the spotlight backdrop ONLY during a step — that's the only
        // time the viewport-spanning blocker exists. During intro /
        // sectionComplete the panel stays at its natural depth so the modal
        // dialog (and its scrim) sits on top, keeping the modal focal.
        position: "relative",
        zIndex: controller.isOnStep ? panelLayer : undefined,
        borderLeft: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        transition: "width 300ms ease",
        width: collapsed ? RAIL_WIDTH : RAIL_WIDTH + CONTENT_WIDTH,
      }}
    >
      <Stack
        alignItems="center"
        sx={{
          width: RAIL_WIDTH,
          flexShrink: 0,
          py: 1,
          gap: 1,
          borderRight: collapsed ? 0 : 1,
          borderColor: "divider",
        }}
      >
        <Tooltip title={collapsed ? "Expand walkthrough" : "Collapse walkthrough"} placement="left">
          <IconButton
            size="small"
            onClick={toggle}
            aria-label={collapsed ? "Expand walkthrough" : "Collapse walkthrough"}
            sx={{ color: "text.secondary" }}
          >
            {collapsed ? <ChevronLeftIcon sx={{ fontSize: 20 }} /> : <ChevronRightIcon sx={{ fontSize: 20 }} />}
          </IconButton>
        </Tooltip>

        {collapsed ? (
          <Stack alignItems="center" spacing={1} sx={{ flex: 1, minHeight: 0, width: "100%", pb: 1 }}>
            <TourOutlinedIcon sx={{ fontSize: 18, color: "secondary.main" }} />
            {controller.isRunning ? (
              <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: 600 }}>
                {controller.currentSectionIndex + 1}/{TASK_TOUR_SECTIONS.length}
              </Typography>
            ) : null}
            <Box sx={{ flex: 1, width: 4, borderRadius: 2, bgcolor: "action.hover", position: "relative", overflow: "hidden", minHeight: 24 }}>
              <Box sx={{ position: "absolute", left: 0, right: 0, bottom: 0, height: `${progressPct}%`, bgcolor: "secondary.main" }} />
            </Box>
          </Stack>
        ) : null}
      </Stack>

      {!collapsed ? (
        <Box sx={{ width: CONTENT_WIDTH, flexShrink: 0, height: "100%", overflow: "hidden" }}>
          {controller.isRunning ? (
            <ChecklistPanelBody
              currentSectionIndex={controller.currentSectionIndex}
              currentItemIndex={controller.currentItemIndex}
              activeStepContent={controller.activeStepContent}
              targetLostHint={controller.targetLostHint}
              completedItemKeys={controller.completedItemKeys}
              totalProgress={controller.totalProgress}
              onSelectItem={controller.onSelectItem}
              onToggleItem={controller.onToggleItem}
              onSelectSection={controller.onSelectSection}
              onPrevSection={controller.onPrevSection}
              onNextSection={controller.onNextSection}
              onClose={controller.onClose}
            />
          ) : (
            <Stack spacing={2} sx={{ p: 2.5, height: "100%" }}>
              <Stack direction="row" alignItems="center" spacing={1.25}>
                <Box
                  aria-hidden
                  sx={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    flexShrink: 0,
                    bgcolor: "secondary.dark",
                    color: "common.white",
                  }}
                >
                  <TourOutlinedIcon sx={{ fontSize: 18 }} />
                </Box>
                <Typography variant="caption" sx={{ fontWeight: 600, letterSpacing: 0.2, color: "text.secondary" }}>
                  {TASK_TOUR_SHORT_NAME} · Guided tour
                </Typography>
              </Stack>
              <Typography variant="body2" sx={{ color: "text.primary" }}>
                Your walkthrough is paused. Pick up where you left off:
              </Typography>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.primary" }}>
                {resumeLabel}
              </Typography>
              <Button variant="contained" color="secondary" onClick={handleResume} sx={{ alignSelf: "flex-start" }}>
                Resume tour
              </Button>
            </Stack>
          )}
        </Box>
      ) : null}
    </Box>
  );
}
