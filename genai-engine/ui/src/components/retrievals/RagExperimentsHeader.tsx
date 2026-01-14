import { Add, Clear, PlayArrow, Settings, Science, History, Save } from "@mui/icons-material";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

import { useRagPanels } from "./RagPanelsContext";
import { MAX_PANELS } from "./ragPanelsReducer";

interface RagExperimentsHeaderProps {
  onManageProviders: () => void;
  onRunExperiment: () => void;
  onToggleHistory: () => void;
  notebookName?: string;
  hasNotebook?: boolean;
  historyOpen?: boolean;
}

export const RagExperimentsHeader: React.FC<RagExperimentsHeaderProps> = ({
  onManageProviders,
  onRunExperiment,
  onToggleHistory,
  notebookName,
  hasNotebook = false,
  historyOpen = false,
}) => {
  const { state, setSharedQuery, addPanel, runAllPanels, canAddPanel, saveNotebookState, isDirty } = useRagPanels();
  const [isSaving, setIsSaving] = useState(false);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSharedQuery(e.target.value);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveNotebookState();
    } finally {
      setIsSaving(false);
    }
  };

  const handleClearQuery = () => {
    setSharedQuery("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      runAllPanels();
    }
  };

  // Check if any panel is ready to search
  const hasReadyPanels = state.panels.some((panel) => panel.providerId);
  const isDisabled = !state.sharedQuery.trim() || !hasReadyPanels || state.isRunningAll;

  // Count panels with active searches
  const loadingCount = state.panels.filter((p) => p.isLoading).length;

  return (
    <Stack
      sx={{
        px: 3,
        py: 1.5,
        backgroundColor: "white",
        borderBottom: 1,
        borderColor: "divider",
        gap: 1.5,
      }}
    >
      {/* Row 1: Title + Query Input + Run */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        {/* Title */}
        <Typography variant="h6" sx={{ fontWeight: 600, whiteSpace: "nowrap", color: "black", minWidth: "fit-content" }}>
          {notebookName || "RAG Playground"}
        </Typography>

        {/* Shared Query Input */}
        <TextField
          placeholder="Enter search query..."
          value={state.sharedQuery}
          onChange={handleQueryChange}
          onKeyDown={handleKeyDown}
          size="small"
          fullWidth
          sx={{
            "& .MuiOutlinedInput-root": {
              backgroundColor: "white",
            },
          }}
          slotProps={{
            input: {
              endAdornment: state.sharedQuery && (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={handleClearQuery} edge="end">
                    <Clear fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            },
          }}
        />

        {/* Run Button */}
        <Tooltip
          title={
            !state.sharedQuery.trim()
              ? "Enter a query to search"
              : !hasReadyPanels
                ? "Configure at least one panel"
                : state.isRunningAll
                  ? "Running..."
                  : "Run on all panels (Enter)"
          }
        >
          <span>
            <Button
              variant="contained"
              onClick={() => runAllPanels()}
              disabled={isDisabled}
              startIcon={state.isRunningAll ? <CircularProgress size={16} color="inherit" /> : <PlayArrow />}
              sx={{ whiteSpace: "nowrap" }}
            >
              {state.isRunningAll ? `(${loadingCount})` : "Run"}
            </Button>
          </span>
        </Tooltip>
      </Box>

      {/* Row 2: Action buttons */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        {/* Add Panel */}
        <Tooltip title={canAddPanel ? "Add panel" : `Max ${MAX_PANELS} panels`}>
          <span>
            <Button size="small" variant="outlined" onClick={() => addPanel()} disabled={!canAddPanel} startIcon={<Add />}>
              Panel
            </Button>
          </span>
        </Tooltip>

        {/* Panel Count */}
        <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: "nowrap" }}>
          {state.panels.length}/{MAX_PANELS}
        </Typography>

        {/* Notebook-specific buttons */}
        {hasNotebook && (
          <>
            {/* Save */}
            <Tooltip title={isDirty ? "Save unsaved changes" : "No unsaved changes"}>
              <span>
                <Button
                  size="small"
                  variant={isDirty ? "contained" : "outlined"}
                  onClick={handleSave}
                  disabled={isSaving || !isDirty}
                  startIcon={isSaving ? <CircularProgress size={14} color="inherit" /> : <Save />}
                  sx={{
                    ...(isDirty && {
                      backgroundColor: "#f97316",
                      "&:hover": {
                        backgroundColor: "#ea580c",
                      },
                    }),
                  }}
                >
                  {isSaving ? "Saving" : isDirty ? "Save" : "Saved"}
                </Button>
              </span>
            </Tooltip>

            {/* Run Experiment */}
            <Tooltip title={hasReadyPanels ? "Run experiment" : "Configure a panel first"}>
              <span>
                <Button
                  size="small"
                  variant="contained"
                  color="secondary"
                  onClick={onRunExperiment}
                  disabled={!hasReadyPanels}
                  startIcon={<Science />}
                >
                  Experiment
                </Button>
              </span>
            </Tooltip>

            {/* History */}
            <Tooltip title="History">
              <IconButton
                size="small"
                onClick={onToggleHistory}
                sx={{
                  border: 1,
                  borderColor: historyOpen ? "primary.main" : "divider",
                  backgroundColor: historyOpen ? "primary.50" : "transparent",
                }}
              >
                <History fontSize="small" color={historyOpen ? "primary" : "inherit"} />
              </IconButton>
            </Tooltip>
          </>
        )}

        {/* Spacer */}
        <Box sx={{ flex: 1 }} />

        {/* Manage Providers */}
        <Tooltip title="Manage Providers">
          <IconButton size="small" onClick={onManageProviders} sx={{ border: 1, borderColor: "divider" }}>
            <Settings fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Stack>
  );
};
