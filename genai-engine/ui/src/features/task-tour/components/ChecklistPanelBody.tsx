import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import EastIcon from "@mui/icons-material/East";
import WestIcon from "@mui/icons-material/West";
import { Box, Button, IconButton, LinearProgress, Stack, Tooltip, Typography } from "@mui/material";

import { TASK_TOUR_SECTIONS, TASK_TOUR_TITLE } from "../data";
import type { ChecklistController } from "../hooks/useChecklistController";
import { isSectionComplete, itemKey } from "../progress";

export interface ChecklistPanelBodyProps {
  /**
   * Engine-backed data + handlers from {@link useChecklistController}. The
   * panel is purely presentational; every value and callback it renders comes
   * from this single controller object.
   */
  controller: ChecklistController;
}

/**
 * Presentational checklist: section pips, the current section's title, an
 * interactive checklist of items, and progress controls. Fills its container
 * (the {@link TourSidePanel} supplies the surface, border, and width); it is
 * no longer floating or draggable — collapsing is handled by the panel's
 * chevron, and dismissing by the header close button.
 */
export function ChecklistPanelBody({ controller }: ChecklistPanelBodyProps) {
  const {
    currentSectionIndex,
    currentItemIndex,
    activeStepContent,
    targetLostHint,
    completedItemKeys,
    totalProgress,
    onSelectItem,
    onToggleItem,
    onSelectSection,
    onPrevSection,
    onNextSection,
    onClose,
  } = controller;

  const section = TASK_TOUR_SECTIONS[currentSectionIndex];
  if (!section) return null;
  const items = section.items;
  const stepsInSection = Math.max(1, items.length);
  const sectionStepLabel =
    items.length === 0 ? "Intro" : currentItemIndex >= 0 ? `Step ${currentItemIndex + 1} of ${stepsInSection}` : `Step 1 of ${stepsInSection}`;
  const sectionLabel = `Section ${currentSectionIndex + 1} of ${TASK_TOUR_SECTIONS.length}`;

  return (
    <Stack sx={{ height: "100%", minWidth: 0 }}>
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ p: 1.75, borderBottom: 1, borderColor: "divider", userSelect: "none" }}>
        <Box
          sx={{
            display: "inline-flex",
            alignItems: "center",
            px: 1,
            py: 0.25,
            borderRadius: 5,
            bgcolor: "secondary.light",
            color: "secondary.dark",
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: 0.5,
          }}
        >
          {currentSectionIndex + 1}/{TASK_TOUR_SECTIONS.length}
        </Box>
        <Typography
          variant="body2"
          sx={{ fontWeight: 600, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
        >
          {TASK_TOUR_TITLE}
        </Typography>
        <Tooltip title="Hide walkthrough">
          <IconButton aria-label="Hide walkthrough" size="small" onClick={onClose} sx={{ color: "text.disabled" }}>
            <CloseIcon sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
      </Stack>

      <LinearProgress
        variant="determinate"
        value={Math.min(100, Math.max(0, totalProgress * 100))}
        sx={{
          height: 3,
          bgcolor: "action.hover",
          "& .MuiLinearProgress-bar": { bgcolor: "secondary.main" },
        }}
      />

      <Stack direction="row" spacing={0.5} sx={{ px: 1.5, py: 1, borderBottom: 1, borderColor: "divider", overflowX: "auto" }}>
        {TASK_TOUR_SECTIONS.map((s, i) => {
          const done = isSectionComplete(s, completedItemKeys);
          const active = i === currentSectionIndex;
          return (
            <Box
              key={s.id}
              onClick={() => onSelectSection(i)}
              sx={{
                flexShrink: 0,
                display: "inline-flex",
                alignItems: "center",
                gap: 0.25,
                px: 1,
                py: 0.5,
                borderRadius: 5,
                fontSize: 10,
                fontWeight: 500,
                cursor: "pointer",
                color: active ? "common.white" : done ? "success.dark" : "text.secondary",
                bgcolor: active ? "secondary.main" : done ? "success.50" : "action.hover",
              }}
            >
              {done ? <CheckIcon sx={{ fontSize: 11 }} /> : null}
              {i + 1}
            </Box>
          );
        })}
      </Stack>

      <Box sx={{ px: 2, pt: 1.75, pb: 0.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, color: "text.primary" }}>
          {section.title}
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {section.kicker}
        </Typography>
      </Box>

      <Box sx={{ px: 1, pb: 1.25, overflowY: "auto", flex: 1 }}>
        {items.length === 0 ? (
          <Stack direction="row" spacing={1.25} alignItems="center" sx={{ p: 1.25, borderRadius: 1 }}>
            <Box
              sx={{
                width: 20,
                height: 20,
                borderRadius: "50%",
                border: 1.5,
                borderColor: "divider",
                flexShrink: 0,
              }}
            />
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              Read the intro and continue.
            </Typography>
          </Stack>
        ) : (
          items.map((item, idx) => {
            const done = completedItemKeys.has(itemKey(section.id, item.id));
            const active = !done && idx === currentItemIndex;
            return (
              <Stack
                key={item.id}
                direction="row"
                alignItems="flex-start"
                spacing={1.25}
                onClick={() => onSelectItem(item, idx)}
                sx={{
                  p: 1.25,
                  borderRadius: 1,
                  cursor: "pointer",
                  bgcolor: active ? "secondary.light" : "transparent",
                  transition: "background-color 0.12s",
                  "&:hover": { bgcolor: active ? "secondary.light" : "action.hover" },
                }}
              >
                <Box
                  role="button"
                  aria-label={done ? "Mark step incomplete" : "Mark step complete"}
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleItem(item);
                  }}
                  sx={{
                    flexShrink: 0,
                    width: 20,
                    height: 20,
                    mt: 0.125,
                    borderRadius: "50%",
                    border: 1.5,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "background-color 0.15s, border-color 0.15s, color 0.15s",
                    bgcolor: done ? "secondary.main" : "background.paper",
                    borderColor: done ? "secondary.main" : active ? "secondary.main" : "divider",
                    color: done ? "common.white" : "transparent",
                  }}
                >
                  {done ? <CheckIcon sx={{ fontSize: 12 }} /> : null}
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      color: active ? "secondary.dark" : "text.primary",
                      fontWeight: active ? 500 : 400,
                      textDecoration: done ? "line-through" : "none",
                      lineHeight: 1.4,
                    }}
                  >
                    {item.title}
                  </Typography>
                  {active && activeStepContent != null ? (
                    typeof activeStepContent === "string" ? (
                      <Typography variant="caption" sx={{ color: "common.black", display: "block", mt: 0.5, lineHeight: 1.45 }}>
                        {activeStepContent}
                      </Typography>
                    ) : (
                      <Box sx={{ color: "common.black", display: "block", mt: 0.5, fontSize: 12, lineHeight: 1.45 }}>{activeStepContent}</Box>
                    )
                  ) : null}
                  {active && targetLostHint ? (
                    <Typography variant="caption" sx={{ color: "warning.dark", display: "block", mt: 0.5, lineHeight: 1.45 }}>
                      {targetLostHint}
                    </Typography>
                  ) : null}
                </Box>
              </Stack>
            );
          })
        )}
      </Box>

      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
        <Stack spacing={0} sx={{ minWidth: 0 }}>
          <Typography variant="caption" sx={{ color: "text.secondary", whiteSpace: "nowrap" }}>
            {sectionStepLabel}
          </Typography>
          <Typography variant="caption" sx={{ color: "text.secondary", whiteSpace: "nowrap" }}>
            {sectionLabel}
          </Typography>
        </Stack>
        <Stack direction="row" spacing={0.75}>
          <Button
            size="small"
            variant="text"
            color="inherit"
            startIcon={<WestIcon sx={{ fontSize: 14 }} />}
            onClick={onPrevSection}
            disabled={currentSectionIndex === 0}
            sx={{ minWidth: 0, color: "text.secondary" }}
          >
            Prev
          </Button>
          <Button
            size="small"
            variant="outlined"
            endIcon={<EastIcon sx={{ fontSize: 14 }} />}
            onClick={onNextSection}
            disabled={currentSectionIndex === TASK_TOUR_SECTIONS.length - 1}
            sx={{ minWidth: 0 }}
          >
            Next
          </Button>
        </Stack>
      </Stack>
    </Stack>
  );
}
