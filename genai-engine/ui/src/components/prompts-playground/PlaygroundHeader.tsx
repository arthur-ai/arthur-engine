import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckIcon from "@mui/icons-material/Check";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import TuneIcon from "@mui/icons-material/Tune";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import VariableInputs from "./VariableInputs";

import { EditableTitle } from "@/components/common";
import { useTask } from "@/hooks/useTask";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";

export interface PlaygroundHeaderProps {
  notebookId: string | null;
  saveStatus: "saved" | "saving" | "unsaved";
  notebookName: string;
  onSaveRename: (newName: string) => Promise<void>;
  isRenamePending: boolean;
  onManualSave: () => void;
  configDrawerOpen: boolean;
  configModeActive: boolean;
  experimentConfig: Partial<PromptExperimentDetail> | null;
  onToggleConfigDrawer: () => void;
  blankVariablesCount: number;
  onAddPrompt: () => void;
  runAllDisabledReason: string | null;
  onRunAllPrompts: () => void;
}

/**
 * Header bar for the Prompts Playground: back button, notebook name/rename,
 * save status, and action buttons (config, variables, add prompt, run all).
 */
export default function PlaygroundHeader({
  notebookId,
  saveStatus,
  notebookName,
  onSaveRename,
  isRenamePending,
  onManualSave,
  configDrawerOpen,
  configModeActive,
  experimentConfig,
  onToggleConfigDrawer,
  blankVariablesCount,
  onAddPrompt,
  runAllDisabledReason,
  onRunAllPrompts,
}: PlaygroundHeaderProps) {
  const navigate = useNavigate();
  const { task } = useTask();
  const variablesButtonRef = useRef<HTMLButtonElement>(null);
  const [variablesDrawerOpen, setVariablesDrawerOpen] = useState(false);

  const toggleVariablesDrawer = () => {
    setVariablesDrawerOpen((prev) => !prev);
  };

  return (
    <Container component="div" maxWidth={false} disableGutters className="p-2 mt-1 shrink-0" sx={{ backgroundColor: "background.default" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
        <Stack direction="row" alignItems="center" spacing={2}>
          {notebookId && (
            <Stack alignItems="flex-start">
              <Button
                size="small"
                variant="text"
                startIcon={<ArrowBackIcon />}
                color="inherit"
                onClick={() => navigate(`/tasks/${task?.id}/prompts`)}
                sx={{ color: "text.primary" }}
              >
                Back to Notebooks
              </Button>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Tooltip
                  title={saveStatus === "saved" ? "All changes saved" : saveStatus === "saving" ? "Saving changes..." : "Click to save changes"}
                  arrow
                >
                  <span>
                    <Button
                      size="small"
                      variant={saveStatus === "unsaved" ? "contained" : "outlined"}
                      onClick={() => {
                        if (saveStatus === "unsaved") {
                          onManualSave();
                        }
                      }}
                      disabled={saveStatus !== "unsaved"}
                      startIcon={
                        saveStatus === "saving" ? (
                          <CircularProgress size={14} color="inherit" />
                        ) : saveStatus === "saved" ? (
                          <CheckIcon />
                        ) : (
                          <SaveIcon />
                        )
                      }
                      sx={{
                        minWidth: "auto",
                        px: 1.5,
                        py: 0.5,
                        fontSize: "0.75rem",
                        textTransform: "none",
                        color: saveStatus === "saved" ? "success.main" : undefined,
                        borderColor: saveStatus === "saved" ? "success.main" : undefined,
                        "&.Mui-disabled": {
                          color: saveStatus === "saved" ? "success.main" : undefined,
                          borderColor: saveStatus === "saved" ? "success.main" : undefined,
                        },
                      }}
                    >
                      {saveStatus === "saved" ? "Saved" : saveStatus === "saving" ? "Saving..." : "Save"}
                    </Button>
                  </span>
                </Tooltip>
                <EditableTitle
                  value={notebookName}
                  onSave={onSaveRename}
                  isPending={isRenamePending}
                  fallbackText="Notebook"
                  typographySx={{ fontWeight: 600, color: "text.primary" }}
                />
              </Box>
            </Stack>
          )}
        </Stack>

        <Stack direction="row" alignItems="center" spacing={2}>
          <Button variant={configDrawerOpen ? "contained" : "outlined"} size="small" onClick={onToggleConfigDrawer} startIcon={<InfoOutlinedIcon />}>
            {configModeActive && experimentConfig ? "View Config" : "Set Config"}
          </Button>
          <Box sx={{ position: "relative" }}>
            <Badge badgeContent={blankVariablesCount} color="error" overlap="rectangular">
              <Button
                ref={variablesButtonRef}
                variant={variablesDrawerOpen ? "contained" : "outlined"}
                color="primary"
                size="small"
                onClick={toggleVariablesDrawer}
                startIcon={<TuneIcon />}
              >
                Variables
              </Button>
              <Popover
                open={variablesDrawerOpen}
                onClose={toggleVariablesDrawer}
                anchorEl={variablesButtonRef.current}
                anchorOrigin={{
                  vertical: "bottom",
                  horizontal: "left",
                }}
                slotProps={{
                  paper: {
                    sx: { width: "400px", maxHeight: "500px" },
                  },
                }}
                sx={{ marginTop: "6px" }}
              >
                <VariableInputs />
              </Popover>
            </Badge>
          </Box>
          <Button variant="contained" size="small" onClick={onAddPrompt} startIcon={<AddIcon />}>
            Add Prompt
          </Button>
          <Tooltip title={runAllDisabledReason || "Run All Prompts"} arrow>
            <span>
              <Button variant="contained" size="small" onClick={onRunAllPrompts} startIcon={<PlayArrowIcon />} disabled={!!runAllDisabledReason}>
                Run All Prompts
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Stack>
    </Container>
  );
}
