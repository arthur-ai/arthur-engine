import { Add, ArrowBack, Clear, Edit, PlayArrow, Settings, Science, History, Save } from "@mui/icons-material";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useRagPanels } from "./RagPanelsContext";
import { MAX_PANELS } from "./ragPanelsReducer";

import { useUpdateRagNotebookMutation } from "@/hooks/useRagNotebooks";

interface RagExperimentsHeaderProps {
  onManageProviders: () => void;
  onRunExperiment: () => void;
  onToggleHistory: () => void;
  notebookName?: string;
  notebookId?: string | null;
  notebookDescription?: string | null;
  hasNotebook?: boolean;
  historyOpen?: boolean;
}

export const RagExperimentsHeader: React.FC<RagExperimentsHeaderProps> = ({
  onManageProviders,
  onRunExperiment,
  onToggleHistory,
  notebookName,
  notebookId,
  notebookDescription,
  hasNotebook = false,
  historyOpen = false,
}) => {
  const { id: taskId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { state, setSharedQuery, addPanel, runAllPanels, canAddPanel, saveNotebookState, isDirty } = useRagPanels();
  const [isSaving, setIsSaving] = useState(false);
  const updateMutation = useUpdateRagNotebookMutation();
  const [isRenaming, setIsRenaming] = useState(false);
  const [newNotebookName, setNewNotebookName] = useState(notebookName ?? "");

  useEffect(() => {
    if (notebookName) setNewNotebookName(notebookName);
  }, [notebookName]);

  const handleStartRename = () => {
    setNewNotebookName(notebookName ?? "");
    setIsRenaming(true);
  };

  const handleCancelRename = () => {
    setIsRenaming(false);
    setNewNotebookName(notebookName ?? "");
  };

  const handleSaveRename = async () => {
    if (updateMutation.isPending) return;
    const trimmed = newNotebookName.trim();
    if (!trimmed || !notebookId || trimmed === notebookName) {
      handleCancelRename();
      return;
    }
    setIsRenaming(false);
    await updateMutation.mutateAsync({ notebookId, request: { name: trimmed, description: notebookDescription } });
  };

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
  const hasReadyPanels = state.panels.some((panel) => panel.providerId && panel.collection);
  const isDisabled = !state.sharedQuery.trim() || !hasReadyPanels || state.isRunningAll;

  // Count panels with active searches
  const loadingCount = state.panels.filter((p) => p.isLoading).length;

  return (
    <Stack
      sx={{
        px: 3,
        py: 1.5,
        backgroundColor: "background.paper",
        borderBottom: 1,
        borderColor: "divider",
        gap: 1.5,
      }}
    >
      {/* Back to Notebooks */}
      {hasNotebook && (
        <Button
          size="small"
          variant="text"
          startIcon={<ArrowBack />}
          color="inherit"
          onClick={() => navigate(`/tasks/${taskId}/rag-notebooks`)}
          sx={{ color: "text.primary", alignSelf: "flex-start" }}
        >
          Back to Notebooks
        </Button>
      )}
      {/* Row 1: Title + Query Input + Run */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        {/* Title */}
        {hasNotebook && isRenaming ? (
          <TextField
            variant="filled"
            size="small"
            value={newNotebookName}
            onChange={(e) => setNewNotebookName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSaveRename();
              else if (e.key === "Escape") handleCancelRename();
            }}
            onBlur={handleSaveRename}
            autoFocus
            sx={{
              minWidth: 200,
              "& .MuiInputBase-root": { fontSize: "1.25rem", fontWeight: 600 },
            }}
          />
        ) : (
          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, minWidth: "fit-content" }}>
            <Typography variant="h6" sx={{ fontWeight: 600, whiteSpace: "nowrap", color: "text.primary" }}>
              {notebookName || "RAG Playground"}
            </Typography>
            {hasNotebook && (
              <IconButton
                size="small"
                onClick={handleStartRename}
                sx={{
                  padding: 0.5,
                  color: "text.secondary",
                  "&:hover": { color: "text.primary", backgroundColor: "action.hover" },
                }}
              >
                <Edit sx={{ fontSize: "1rem" }} />
              </IconButton>
            )}
          </Box>
        )}

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
              backgroundColor: "background.paper",
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
