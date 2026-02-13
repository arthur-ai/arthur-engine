import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckIcon from "@mui/icons-material/Check";
import EditIcon from "@mui/icons-material/Edit";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import TuneIcon from "@mui/icons-material/Tune";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import VariableInputs from "./VariableInputs";

import { useTask } from "@/hooks/useTask";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";

export interface PlaygroundHeaderProps {
  notebookId: string | null;
  isRenaming: boolean;
  newNotebookName: string;
  setNewNotebookName: (name: string) => void;
  saveStatus: "saved" | "saving" | "unsaved";
  notebookName: string;
  onStartRename: () => void;
  onSaveRename: () => void;
  onCancelRename: () => void;
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
  isRenaming,
  newNotebookName,
  setNewNotebookName,
  saveStatus,
  notebookName,
  onStartRename,
  onSaveRename,
  onCancelRename,
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
    <Container component="div" maxWidth={false} disableGutters className="p-2 mt-1 bg-gray-300 dark:bg-gray-900 shrink-0">
      <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
        <Stack direction="row" alignItems="center" spacing={2}>
          {notebookId && (
            <>
              <IconButton
                size="small"
                onClick={() => navigate(`/tasks/${task?.id}/notebooks`)}
                sx={{
                  color: "text.secondary",
                  "&:hover": { backgroundColor: "action.hover" },
                }}
              >
                <ArrowBackIcon fontSize="small" />
              </IconButton>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {isRenaming ? (
                  <TextField
                    size="small"
                    value={newNotebookName}
                    onChange={(e) => setNewNotebookName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        onSaveRename();
                      } else if (e.key === "Escape") {
                        onCancelRename();
                      }
                    }}
                    onBlur={onSaveRename}
                    autoFocus
                    sx={{
                      "& .MuiInputBase-root": {
                        fontSize: "0.875rem",
                        fontWeight: 600,
                      },
                    }}
                  />
                ) : (
                  <>
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
                          startIcon={saveStatus === "saved" ? <CheckIcon /> : <SaveIcon />}
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
                    <Typography variant="body2" sx={{ fontWeight: 600, color: "text.primary" }}>
                      {notebookName || "Notebook"}
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={onStartRename}
                      sx={{
                        padding: 0.5,
                        color: "text.secondary",
                        "&:hover": {
                          color: "text.primary",
                          backgroundColor: "action.hover",
                        },
                      }}
                    >
                      <EditIcon sx={{ fontSize: "1rem" }} />
                    </IconButton>
                  </>
                )}
              </Box>
            </>
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
