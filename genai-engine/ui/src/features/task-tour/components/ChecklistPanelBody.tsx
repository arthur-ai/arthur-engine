import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import EastIcon from "@mui/icons-material/East";
import WestIcon from "@mui/icons-material/West";
import { Box, Button, IconButton, LinearProgress, Stack, Tooltip, Typography, useMediaQuery } from "@mui/material";
import { useLayoutEffect, useRef } from "react";

import { TASK_TOUR_SECTIONS, TASK_TOUR_TITLE } from "../data";
import type { ChecklistController } from "../hooks/useChecklistController";
import { isSectionComplete, itemKey } from "../progress";

const ACTIVE_STEP_VALUE = "true";
const ACTIVE_STEP_SELECTOR = `[data-active-step="${ACTIVE_STEP_VALUE}"]`;

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
    occlusionHint,
    onRecoverOcclusion,
    completedItemKeys,
    totalProgress,
    onSelectItem,
    onToggleItem,
    onSelectSection,
    onPrevSection,
    onNextSection,
    onClose,
  } = controller;

  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");

  // Keep the highlighted step with description in view
  useLayoutEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;
    const item = container.querySelector<HTMLElement>(ACTIVE_STEP_SELECTOR);
    if (!item) return;

    const PADDING = 12; // breathing room so the row never rests flush against an edge
    const containerRect = container.getBoundingClientRect();
    const itemRect = item.getBoundingClientRect();
    const itemTop = itemRect.top - containerRect.top + container.scrollTop;
    const itemBottom = itemTop + itemRect.height;
    const viewTop = container.scrollTop;
    const viewBottom = viewTop + container.clientHeight;

    let nextTop: number | null = null;
    if (itemTop < viewTop) {
      // The row's title is clipped above the fold — pull it down into view.
      nextTop = itemTop - PADDING;
    } else if (itemBottom > viewBottom) {
      // The row's description is clipped below the fold — reveal the whole row.
      // If the row is taller than the viewport, prefer the title (start edge)
      // over the tail of the description.
      nextTop = Math.min(itemBottom - container.clientHeight + PADDING, itemTop - PADDING);
    }
    if (nextTop === null) return; // already fully visible — leave the scroll position alone

    container.scrollTo({ top: Math.max(0, nextTop), behavior: reduceMotion ? "auto" : "smooth" });
  }, [currentSectionIndex, currentItemIndex, activeStepContent, targetLostHint, reduceMotion]);

  const section = TASK_TOUR_SECTIONS[currentSectionIndex];
  if (!section) return null;
  const items = section.items;

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

      <Box ref={scrollContainerRef} sx={{ px: 1, pb: 1.25, overflowY: "auto", flex: 1 }}>
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
            const selected = idx === currentItemIndex;
            return (
              <Stack
                key={item.id}
                data-active-step={selected ? ACTIVE_STEP_VALUE : undefined}
                direction="row"
                alignItems="flex-start"
                spacing={1.25}
                onClick={() => onSelectItem(item, idx)}
                sx={{
                  p: 1.25,
                  borderRadius: 1,
                  cursor: "pointer",
                  bgcolor: selected ? "secondary.light" : "transparent",
                  transition: "background-color 0.12s",
                  "&:hover": { bgcolor: selected ? "secondary.light" : "action.hover" },
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
                    borderColor: done ? "secondary.main" : selected ? "secondary.main" : "divider",
                    color: done ? "common.white" : "transparent",
                  }}
                >
                  {done ? <CheckIcon sx={{ fontSize: 12 }} /> : null}
                </Box>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      color: selected ? "secondary.dark" : "text.primary",
                      fontWeight: selected ? 500 : 400,
                      textDecoration: done ? "line-through" : "none",
                      lineHeight: 1.4,
                    }}
                  >
                    {item.title}
                  </Typography>
                  {selected && activeStepContent != null ? (
                    typeof activeStepContent === "string" ? (
                      <Typography variant="caption" sx={{ color: "common.black", display: "block", mt: 0.5, lineHeight: 1.45 }}>
                        {activeStepContent}
                      </Typography>
                    ) : (
                      <Box sx={{ color: "common.black", display: "block", mt: 0.5, fontSize: 12, lineHeight: 1.45 }}>{activeStepContent}</Box>
                    )
                  ) : null}
                  {selected && targetLostHint ? (
                    <Typography variant="caption" sx={(theme) => ({ color: theme.tour.hintColor, display: "block", mt: 0.5, lineHeight: 1.45 })}>
                      {targetLostHint}
                    </Typography>
                  ) : null}
                  {selected && occlusionHint ? (
                    <Box sx={{ mt: 0.75 }} onClick={(e) => e.stopPropagation()}>
                      <Typography variant="caption" sx={(theme) => ({ color: theme.tour.hintColor, display: "block", lineHeight: 1.45 })}>
                        {occlusionHint.message}
                      </Typography>
                      <Button size="small" variant="outlined" onClick={onRecoverOcclusion} sx={{ mt: 0.5 }}>
                        {occlusionHint.actionLabel}
                      </Button>
                    </Box>
                  ) : null}
                </Box>
              </Stack>
            );
          })
        )}
      </Box>

      <Stack direction="row" spacing={1} sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
        <Button
          size="small"
          variant="text"
          color="inherit"
          startIcon={<WestIcon sx={{ fontSize: 14 }} />}
          onClick={onPrevSection}
          disabled={currentSectionIndex === 0}
          sx={{ flex: 1, color: "text.secondary" }}
        >
          Prev
        </Button>
        <Button
          size="small"
          variant="outlined"
          endIcon={<EastIcon sx={{ fontSize: 14 }} />}
          onClick={onNextSection}
          disabled={currentSectionIndex === TASK_TOUR_SECTIONS.length - 1}
          sx={{ flex: 1 }}
        >
          Next
        </Button>
      </Stack>
    </Stack>
  );
}
