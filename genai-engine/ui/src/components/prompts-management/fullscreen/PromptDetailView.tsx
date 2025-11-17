import CloseIcon from "@mui/icons-material/Close";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Popover from "@mui/material/Popover";
import Radio from "@mui/material/Radio";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";

import type { PromptDetailViewProps } from "../types";
import { useAddTagToPromptVersionMutation } from "../hooks/useAddTagToPromptVersionMutation";
import { useDeleteTagFromPromptVersionMutation } from "../hooks/useDeleteTagFromPromptVersionMutation";

import { formatDate } from "@/utils/formatters";

const PromptDetailView = ({ promptData, isLoading, error, promptName, version, latestVersion, taskId, onClose, onRefetch }: PromptDetailViewProps) => {
  const [tagAnchorEl, setTagAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [newTag, setNewTag] = useState("");
  const [tagError, setTagError] = useState("");
  const [promoteToProduction, setPromoteToProduction] = useState(false);

  const addTagMutation = useAddTagToPromptVersionMutation();
  const deleteTagMutation = useDeleteTagFromPromptVersionMutation();

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
    <Box sx={{ p: 3, height: "100%", overflow: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
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
        {onClose && (
          <IconButton onClick={onClose} aria-label="Close">
            <CloseIcon />
          </IconButton>
        )}
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Metadata
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
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
        </Box>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Messages
        </Typography>
        <Box
          component="pre"
          sx={{
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontFamily: "monospace",
            backgroundColor: "grey.50",
            p: 2,
            borderRadius: 1,
            overflow: "auto",
            fontSize: "0.875rem",
          }}
        >
          {JSON.stringify(promptData.messages, null, 2)}
        </Box>
      </Paper>

      {promptData.config && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Configuration
          </Typography>
          <Box
            component="pre"
            sx={{
              backgroundColor: "grey.50",
              p: 2,
              borderRadius: 1,
              overflow: "auto",
              fontSize: "0.875rem",
              fontFamily: "monospace",
            }}
          >
            {JSON.stringify(promptData.config, null, 2)}
          </Box>
        </Paper>
      )}

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
    </Box>
  );
};

export default PromptDetailView;
