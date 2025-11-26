import CloseIcon from "@mui/icons-material/Close";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import SettingsIcon from "@mui/icons-material/Settings";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Popover from "@mui/material/Popover";
import Radio from "@mui/material/Radio";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { useAddTagToPromptVersionMutation } from "../hooks/useAddTagToPromptVersionMutation";
import { useDeleteTagFromPromptVersionMutation } from "../hooks/useDeleteTagFromPromptVersionMutation";
import type { PromptDetailViewProps } from "../types";

import MustacheHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { useCreateNotebookMutation } from "@/hooks/useNotebooks";
import { useApi } from "@/hooks/useApi";
import { formatDate } from "@/utils/formatters";

const PromptDetailView = ({ promptData, isLoading, error, promptName, version, latestVersion, taskId, onClose, onRefetch }: PromptDetailViewProps) => {
  const [tagAnchorEl, setTagAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [newTag, setNewTag] = useState("");
  const [tagError, setTagError] = useState("");
  const [promoteToProduction, setPromoteToProduction] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);

  const addTagMutation = useAddTagToPromptVersionMutation();
  const deleteTagMutation = useDeleteTagFromPromptVersionMutation();
  const apiClient = useApi();
  const navigate = useNavigate();

  const createNotebookMutation = useCreateNotebookMutation(taskId, (notebook) => {
    // Navigate to the notebook with the prompt loaded (same tab)
    const url = `/tasks/${taskId}/playgrounds/prompts?notebookId=${notebook.id}&promptName=${encodeURIComponent(promptName)}&version=${version}`;
    navigate(url);
  });

  const handleAddTagClick = useCallback((event: React.MouseEvent<HTMLButtonElement>) => {
    setTagAnchorEl(event.currentTarget);
    setNewTag("");
    setTagError("");
    setPromoteToProduction(false);
  }, []);

  const handleAddTagClose = useCallback(() => {
    setTagAnchorEl(null);
    setNewTag("");
    setTagError("");
    setPromoteToProduction(false);
  }, []);

  const handleAddTagConfirm = useCallback(async () => {
    // Check if user is trying to do anything at all
    if (!newTag.trim() && !promoteToProduction) {
      setTagError("Please enter a tag or select 'Promote to Production'");
      return;
    }

    // Check for reserved tag name if a tag was entered
    if (newTag.trim() && newTag.trim().toLowerCase() === "latest") {
      setTagError("'latest' is a reserved keyword and cannot be used as a tag");
      return;
    }

    // Check for duplicate tag if a tag was entered
    if (newTag.trim() && promptData?.tags?.includes(newTag.trim())) {
      setTagError("This tag already exists");
      return;
    }

    if (!taskId || version === null) return;

    try {
      // Add the user-entered tag if provided
      if (newTag.trim()) {
        await addTagMutation.mutateAsync({
          promptName,
          promptVersion: version.toString(),
          taskId,
          data: { tag: newTag.trim() },
        });
      }

      // If promote to production is checked, add the "production" tag
      if (promoteToProduction) {
        await addTagMutation.mutateAsync({
          promptName,
          promptVersion: version.toString(),
          taskId,
          data: { tag: "production" },
        });
      }

      setTagAnchorEl(null);
      setNewTag("");
      setTagError("");
      setPromoteToProduction(false);
      onRefetch?.();
    } catch (err) {
      setTagError(err instanceof Error ? err.message : "Failed to add tag");
    }
  }, [newTag, promoteToProduction, promptData?.tags, taskId, version, promptName, addTagMutation, onRefetch]);

  const tagPopoverOpen = Boolean(tagAnchorEl);

  const handleDeleteTag = useCallback(async (tag: string) => {
    if (!taskId || version === null) return;

    try {
      await deleteTagMutation.mutateAsync({
        promptName,
        promptVersion: version.toString(),
        tag,
        taskId,
      });
      onRefetch?.();
    } catch (err) {
      console.error("Failed to delete tag:", err);
    }
  }, [taskId, version, promptName, deleteTagMutation, onRefetch]);

  const handleOpenInNotebook = useCallback(async () => {
    if (!taskId || version === null || !apiClient) return;

    try {
      const notebookName = `${promptName} v${version}`;

      // Search for a notebook with this exact name using the name filter
      // This is more efficient than fetching all notebooks and filtering client-side
      const response = await apiClient.api.listNotebooksApiV1TasksTaskIdNotebooksGet({
        taskId,
        page: 0,
        page_size: 1, // Only need to check if one exists
        name: notebookName, // Filter by exact name match
      });

      // Check if we found a matching notebook
      const existingNotebook = response.data.data?.[0];

      if (existingNotebook && existingNotebook.name === notebookName) {
        // Navigate to existing notebook (same tab)
        const url = `/tasks/${taskId}/playgrounds/prompts?notebookId=${existingNotebook.id}`;
        navigate(url);
      } else {
        // Create a new notebook with a descriptive name
        await createNotebookMutation.mutateAsync({
          name: notebookName,
          description: `Notebook for prompt ${promptName} version ${version}`,
        });
        // Navigation happens in the onSuccess callback
      }
    } catch (err) {
      console.error("Failed to open notebook:", err);
    }
  }, [taskId, promptName, version, apiClient, createNotebookMutation]);

  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100%",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Error loading prompt: {error.message}</Alert>
      </Box>
    );
  }

  if (!promptData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No prompt data available</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3, flexShrink: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {promptName}
          </Typography>
          {version !== null && <Chip label={`Version ${version}`} size="small" sx={{ height: 24 }} />}
          {version !== null && version === latestVersion && <Chip label="Latest" size="small" color="default" sx={{ height: 24 }} />}
          {promptData.tags && promptData.tags.length > 0 && (
            <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
              {promptData.tags.map((tag) => {
                const isProduction = tag.toLowerCase() === "production";
                return (
                  <Chip
                    key={tag}
                    label={tag}
                    size="small"
                    onDelete={() => handleDeleteTag(tag)}
                    sx={{ height: 24 }}
                    color={isProduction ? "success" : "primary"}
                    variant={isProduction ? "filled" : "outlined"}
                  />
                );
              })}
            </Box>
          )}
          {version !== null && (
            <IconButton size="small" onClick={handleAddTagClick} aria-label="Add tag">
              <LocalOfferIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {!promptData.deleted_at && version !== null && (
            <Button
              variant="outlined"
              size="small"
              onClick={handleOpenInNotebook}
              disabled={createNotebookMutation.isPending}
              sx={{ minWidth: 80 }}
            >
              {createNotebookMutation.isPending ? "Opening..." : "Open in Notebook"}
            </Button>
          )}
          {onClose && (
            <IconButton onClick={onClose} aria-label="Close">
              <CloseIcon />
            </IconButton>
          )}
        </Box>
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 3, flex: 1, minHeight: 0, overflow: "auto" }}>
        <Paper sx={{ p: 3, flexShrink: 0 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Metadata
          </Typography>
          <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "flex-start" }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Model Provider
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {promptData.model_provider}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Model Name
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {promptData.model_name}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Created At
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {promptData.created_at ? formatDate(promptData.created_at) : "N/A"}
              </Typography>
            </Box>
            {promptData.deleted_at && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Deleted At
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500, color: "error.main" }}>
                  {formatDate(promptData.deleted_at)}
                </Typography>
              </Box>
            )}
            {promptData.config && (
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: "block" }}>
                  Configuration
                </Typography>
                <Button
                  variant="text"
                  size="small"
                  startIcon={<SettingsIcon />}
                  onClick={() => setIsConfigModalOpen(true)}
                  sx={{
                    p: 0,
                    minWidth: 0,
                    justifyContent: "flex-start",
                    fontWeight: 500,
                    textTransform: "none",
                    "&:hover": {
                      backgroundColor: "transparent",
                      textDecoration: "underline"
                    }
                  }}
                >
                  View Config
                </Button>
              </Box>
            )}
          </Box>
        </Paper>

        <Paper sx={{ p: 3, display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Messages
          </Typography>
          <Box
            sx={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              flexDirection: "column",
              "& .MuiTextField-root": {
                flex: 1,
                display: "flex",
                flexDirection: "column",
              },
              "& .MuiInputBase-root": {
                flex: 1,
                height: "100%",
                alignItems: "flex-start",
              },
              "& .MuiInputBase-input": {
                height: "100% !important",
                overflow: "auto !important",
              },
            }}
          >
            <MustacheHighlightedTextField
              value={JSON.stringify(promptData.messages, null, 2)}
              onChange={() => {}} // Read-only, no-op
              disabled
              multiline
              minRows={4}
              size="small"
            />
          </Box>
        </Paper>
      </Box>

      <Popover
        open={tagPopoverOpen}
        anchorEl={tagAnchorEl}
        onClose={handleAddTagClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
      >
        <Box sx={{ p: 2, minWidth: 300 }}>
          <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 600 }}>
            Prompt Tags
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: "block" }}>
            Production status and tags to easily identify your prompts.
          </Typography>

          <Divider sx={{ mb: 2 }} />

          <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
            Promote to Production
          </Typography>
          <Box sx={{ mb: 2 }}>
            <FormControlLabel
              control={<Radio checked={promoteToProduction} onChange={(e) => setPromoteToProduction(e.target.checked)} size="small" />}
              label={<Typography variant="caption">Mark this version as production</Typography>}
            />
          </Box>

          <Divider sx={{ mb: 2 }} />

          <Typography variant="body2" sx={{ mb: 1, fontWeight: 600 }}>
            Custom Tag (Optional)
          </Typography>
          <TextField
            autoFocus
            size="small"
            label="Tag Name"
            type="text"
            fullWidth
            variant="outlined"
            value={newTag}
            onChange={(e) => {
              setNewTag(e.target.value);
              setTagError("");
            }}
            error={!!tagError}
            helperText={tagError}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleAddTagConfirm();
              }
            }}
            sx={{ mb: 1.5 }}
          />

          <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
            <Button size="small" onClick={handleAddTagClose} disabled={addTagMutation.isPending}>
              Cancel
            </Button>
            <Button
              size="small"
              onClick={handleAddTagConfirm}
              variant="contained"
              disabled={addTagMutation.isPending}
              startIcon={addTagMutation.isPending ? <CircularProgress size={14} /> : null}
            >
              {addTagMutation.isPending ? "Adding..." : "Save"}
            </Button>
          </Box>
        </Box>
      </Popover>

      <Dialog open={isConfigModalOpen} onClose={() => setIsConfigModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Configuration</DialogTitle>
        <DialogContent>
          <Box
            component="pre"
            sx={{
              backgroundColor: "grey.50",
              p: 2,
              borderRadius: 1,
              overflow: "auto",
              fontSize: "0.875rem",
              fontFamily: "monospace",
              maxHeight: 500,
              m: 0,
            }}
          >
            {promptData?.config ? JSON.stringify(promptData.config, null, 2) : "No configuration available"}
          </Box>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default PromptDetailView;
