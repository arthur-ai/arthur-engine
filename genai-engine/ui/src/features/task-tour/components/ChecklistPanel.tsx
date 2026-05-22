import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import EastIcon from "@mui/icons-material/East";
import WestIcon from "@mui/icons-material/West";
import { Box, Button, IconButton, LinearProgress, Paper, Stack, Tooltip, Typography, useTheme } from "@mui/material";
import type { ReactNode } from "react";

import { TASK_TOUR_SECTIONS, TASK_TOUR_TITLE, type TaskTourItem, type TaskTourSection } from "../data";

export interface ChecklistPanelProps {
  currentSectionIndex: number;
  /** -1 = no active item (stub section). */
  currentItemIndex: number;
  /**
   * Resolved content for the currently active step (i.e. the one rendered
   * under the highlighted row). Comes from the engine's `StepConfig.content`
   * — a `ReactNode` or the result of the function form already evaluated by
   * the parent. `null` when the tour isn't on a real step.
   */
  activeStepContent: ReactNode | null;
  completedItemKeys: ReadonlySet<string>;
  totalItemCount: number;
  totalProgress: number;
  onSelectItem: (item: TaskTourItem, itemIndex: number) => void;
  onToggleItem: (item: TaskTourItem) => void;
  onSelectSection: (sectionIndex: number) => void;
  onPrevSection: () => void;
  onNextSection: () => void;
  onClose: () => void;
}

const PANEL_WIDTH = 320;
const PANEL_Z_INDEX = 1450;

function itemKey(section: TaskTourSection, item: TaskTourItem) {
  return `${section.id}.${item.id}`;
}

function isSectionDone(section: TaskTourSection, completed: ReadonlySet<string>): boolean {
  if (section.items.length === 0) return completed.has(`${section.id}.__intro`);
  return section.items.every((it) => completed.has(itemKey(section, it)));
}

/**
 * Floating bottom-right panel with section pips, the current section's title,
 * an interactive checklist of items, and progress controls. This is the
 * design's "checklist + section nav" widget, rebuilt on MUI tokens.
 */
export function ChecklistPanel({
  currentSectionIndex,
  currentItemIndex,
  activeStepContent,
  completedItemKeys,
  totalItemCount,
  totalProgress,
  onSelectItem,
  onToggleItem,
  onSelectSection,
  onPrevSection,
  onNextSection,
  onClose,
}: ChecklistPanelProps) {
  const theme = useTheme();
  const section = TASK_TOUR_SECTIONS[currentSectionIndex];
  if (!section) return null;
  const items = section.items;

  return (
    <Paper
      elevation={8}
      sx={{
        position: "fixed",
        bottom: 20,
        right: 20,
        width: PANEL_WIDTH,
        maxHeight: "calc(100vh - 40px)",
        display: "flex",
        flexDirection: "column",
        borderRadius: 2.5,
        overflow: "hidden",
        zIndex: PANEL_Z_INDEX,
        border: 1,
        borderColor: "divider",
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1.25} sx={{ p: 1.75, borderBottom: 1, borderColor: "divider" }}>
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
          <IconButton size="small" onClick={onClose} sx={{ color: "text.disabled" }}>
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
          const done = isSectionDone(s, completedItemKeys);
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
              {section.stub ? "Coming soon — section placeholder." : "Read the intro and continue."}
            </Typography>
          </Stack>
        ) : (
          items.map((item, idx) => {
            const done = completedItemKeys.has(itemKey(section, item));
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
                    borderColor: done ? "secondary.main" : active ? "secondary.main" : theme.palette.divider,
                    color: done ? theme.palette.common.white : "transparent",
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
                      <Typography variant="caption" sx={{ color: "black", display: "block", mt: 0.5, lineHeight: 1.45 }}>
                        {activeStepContent}
                      </Typography>
                    ) : (
                      <Box sx={{ color: "black", display: "block", mt: 0.5, fontSize: 12, lineHeight: 1.45 }}>{activeStepContent}</Box>
                    )
                  ) : null}
                </Box>
              </Stack>
            );
          })
        )}
      </Box>

      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {completedItemKeys.size} of {totalItemCount} steps
        </Typography>
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
    </Paper>
  );
}
