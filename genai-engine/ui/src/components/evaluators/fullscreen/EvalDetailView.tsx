import { MustacheHighlightedTextField } from "@arthur/shared-components";
import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
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
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";

import EvalEditModal from "../EvalEditModal";
import { useAddTagToEvalVersionMutation } from "../hooks/useAddTagToEvalVersionMutation";
import { useCreateEvalMutation } from "../hooks/useCreateEvalMutation";
import { useDeleteTagFromEvalVersionMutation } from "../hooks/useDeleteTagFromEvalVersionMutation";
import { useImpactedContinuousEvals } from "../hooks/useImpactedContinuousEvals";
import type { EvalDetailViewProps } from "../types";

import ImpactedCEsDialog from "./ImpactedCEsDialog";

import { useCreateMlEvalMutation } from "@/components/ml-evaluators/hooks/useCreateMlEvalMutation";
import MLEvalFormModal from "@/components/ml-evaluators/MLEvalFormModal";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { ContinuousEvalResponse, CreateEvalRequest, CreateMLEvalRequest, ModelProvider } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

const ML_EDITABLE_TYPES = ["pii", "pii_v1", "toxicity"];

const EvalDetailView = ({ evalData, isLoading, error, evalName, version, latestVersion, taskId, onRefetch }: EvalDetailViewProps) => {
  const [tagAnchorEl, setTagAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [newTag, setNewTag] = useState("");
  const [tagError, setTagError] = useState("");
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isMlEditModalOpen, setIsMlEditModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [impactedCEs, setImpactedCEs] = useState<ContinuousEvalResponse[]>([]);
  const [impactedCEsNewVersion, setImpactedCEsNewVersion] = useState<number>(0);
  const [isImpactedCEsDialogOpen, setIsImpactedCEsDialogOpen] = useState(false);

  const addTagMutation = useAddTagToEvalVersionMutation();
  const deleteTagMutation = useDeleteTagFromEvalVersionMutation();
  const createEvalMutation = useCreateEvalMutation(taskId);
  const createMlEvalMutation = useCreateMlEvalMutation(taskId);
  const { fetchImpactedCEs } = useImpactedContinuousEvals(taskId);
  const { timezone, use24Hour } = useDisplaySettings();

  const handleAddTagClick = useCallback((event: React.MouseEvent<HTMLButtonElement>) => {
    setTagAnchorEl(event.currentTarget);
    setNewTag("");
    setTagError("");
  }, []);

  const handleAddTagClose = useCallback(() => {
    setTagAnchorEl(null);
    setNewTag("");
    setTagError("");
  }, []);

  const handleAddTagConfirm = useCallback(async () => {
    // Check if user entered a tag
    if (!newTag.trim()) {
      setTagError("Please enter a tag");
      return;
    }

    // Check for reserved tag name
    if (newTag.trim().toLowerCase() === "latest") {
      setTagError("'latest' is a reserved keyword and cannot be used as a tag");
      return;
    }

    // Check for duplicate tag
    if (evalData?.tags?.includes(newTag.trim())) {
      setTagError("This tag already exists");
      return;
    }

    if (!taskId || version === null) return;

    try {
      await addTagMutation.mutateAsync({
        evalName,
        evalVersion: version.toString(),
        taskId,
        data: { tag: newTag.trim() },
      });

      setTagAnchorEl(null);
      setNewTag("");
      setTagError("");
      onRefetch?.();
    } catch (err) {
      setTagError(err instanceof Error ? err.message : "Failed to add tag");
    }
  }, [newTag, evalData?.tags, taskId, version, evalName, addTagMutation, onRefetch]);

  const tagPopoverOpen = Boolean(tagAnchorEl);

  const handleDeleteTag = useCallback(
    async (tag: string) => {
      if (!taskId || version === null) return;

      try {
        await deleteTagMutation.mutateAsync({
          evalName,
          evalVersion: version.toString(),
          tag,
          taskId,
        });
        onRefetch?.();
      } catch (err) {
        console.error("Failed to delete tag:", err);
      }
    },
    [taskId, version, evalName, deleteTagMutation, onRefetch]
  );

  const handleEditClick = useCallback(() => {
    setIsEditModalOpen(true);
  }, []);

  const handleEditModalClose = useCallback(() => {
    setIsEditModalOpen(false);
  }, []);

  const handleEditSubmit = useCallback(
    async (data: CreateEvalRequest) => {
      const result = await createEvalMutation.mutateAsync({
        evalName,
        data,
      });
      setIsEditModalOpen(false);
      onRefetch?.(result.version);

      if (result.version != null) {
        try {
          const affected = await fetchImpactedCEs(evalName, result.version);
          if (affected.length > 0) {
            setImpactedCEs(affected);
            setImpactedCEsNewVersion(result.version);
            setIsImpactedCEsDialogOpen(true);
          }
        } catch {
          // Non-critical — don't block the save flow if the check fails
        }
      }
    },
    [evalName, createEvalMutation, onRefetch, fetchImpactedCEs]
  );

  const handleConfigClick = useCallback(() => {
    setIsConfigModalOpen(true);
  }, []);

  const handleConfigModalClose = useCallback(() => {
    setIsConfigModalOpen(false);
  }, []);

  const handleMlEditSubmit = useCallback(
    async (_evalName: string, data: CreateMLEvalRequest) => {
      const result = await createMlEvalMutation.mutateAsync({ evalName, data });
      setIsMlEditModalOpen(false);
      onRefetch?.(result.version);

      try {
        const affected = await fetchImpactedCEs(evalName, result.version);
        if (affected.length > 0) {
          setImpactedCEs(affected);
          setImpactedCEsNewVersion(result.version);
          setIsImpactedCEsDialogOpen(true);
        }
      } catch {
        // Non-critical
      }
    },
    [evalName, createMlEvalMutation, onRefetch, fetchImpactedCEs]
  );
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
        <Alert severity="error">Error loading eval: {error.message}</Alert>
      </Box>
    );
  }

  if (!evalData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No eval data available</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 2, flexShrink: 0 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, flex: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              {evalName}
            </Typography>
            {version !== null && <Chip label={`Version ${version}`} size="small" sx={{ height: 24 }} />}
            {version !== null && version === latestVersion && <Chip label="Latest" size="small" color="default" sx={{ height: 24 }} />}
            {evalData.tags && evalData.tags.length > 0 && (
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {evalData.tags.map((tag) => (
                  <Chip
                    key={tag}
                    label={tag}
                    size="small"
                    onDelete={() => handleDeleteTag(tag)}
                    sx={{ height: 24 }}
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
            )}
            {version !== null && (
              <IconButton size="small" onClick={handleAddTagClick} aria-label="Add tag">
                <LocalOfferIcon fontSize="small" />
              </IconButton>
            )}
          </Box>

          <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap", alignItems: "center" }}>
            {evalData.model_provider && evalData.model_name && (
              <Box sx={{ display: "flex", gap: 0.5, alignItems: "baseline" }}>
                <Typography variant="caption" color="text.secondary">
                  Model:
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {evalData.model_provider} / {evalData.model_name}
                </Typography>
              </Box>
            )}
            {evalData.eval_type && evalData.eval_type !== "llm_as_a_judge" && (
              <Box sx={{ display: "flex", gap: 0.5, alignItems: "baseline" }}>
                <Typography variant="caption" color="text.secondary">
                  Type:
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {evalData.eval_type}
                </Typography>
              </Box>
            )}
            <Box sx={{ display: "flex", gap: 0.5, alignItems: "baseline" }}>
              <Typography variant="caption" color="text.secondary">
                Created:
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {evalData.created_at ? formatDateInTimezone(evalData.created_at, timezone, { hour12: !use24Hour }) : "N/A"}
              </Typography>
            </Box>
            {evalData.deleted_at && (
              <Box sx={{ display: "flex", gap: 0.5, alignItems: "baseline" }}>
                <Typography variant="caption" color="text.secondary">
                  Deleted:
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 500, color: "error.main" }}>
                  {formatDateInTimezone(evalData.deleted_at, timezone, { hour12: !use24Hour })}
                </Typography>
              </Box>
            )}
            <Tooltip title="View Configuration">
              <IconButton size="small" onClick={handleConfigClick} aria-label="View configuration">
                <SettingsIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {!evalData.deleted_at && evalData.eval_type === "llm_as_a_judge" && (
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={handleEditClick} sx={{ minWidth: 80 }}>
              Edit
            </Button>
          )}
          {!evalData.deleted_at && ML_EDITABLE_TYPES.includes(evalData.eval_type ?? "") && (
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => setIsMlEditModalOpen(true)} sx={{ minWidth: 80 }}>
              Edit
            </Button>
          )}
        </Box>
      </Box>

      {evalData.eval_type === "llm_as_a_judge" && (
        <Paper sx={{ p: 3, display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Instructions
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
              value={evalData.instructions ?? ""}
              onChange={() => {}} // Read-only, no-op
              disabled
              multiline
              minRows={4}
              size="small"
            />
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
            Evaluator Tags
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: "block" }}>
            Tags to easily identify your evaluators.
          </Typography>

          <Divider sx={{ mb: 2 }} />

          <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 600 }}>
            Add Tag
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: "block" }}>
            Add a tag to this evaluator version
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

      <Dialog open={isConfigModalOpen} onClose={handleConfigModalClose} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Configuration
            </Typography>
            <IconButton onClick={handleConfigModalClose} size="small" aria-label="Close">
              <CloseIcon />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box
            component="pre"
            sx={{
              backgroundColor: "action.hover",
              p: 2,
              borderRadius: 1,
              overflow: "auto",
              fontSize: "0.875rem",
              fontFamily: "monospace",
              maxHeight: 500,
              mt: 1,
            }}
          >
            {evalData.config ? JSON.stringify(evalData.config, null, 2) : "{}"}
          </Box>
        </DialogContent>
      </Dialog>

      {evalData && (
        <EvalEditModal
          open={isEditModalOpen}
          onClose={handleEditModalClose}
          onSubmit={handleEditSubmit}
          isLoading={createEvalMutation.isPending}
          evalName={evalName}
          initialInstructions={evalData.instructions ?? ""}
          initialModelProvider={evalData.model_provider ?? "" as ModelProvider}
          initialModelName={evalData.model_name ?? ""}
        />
      )}

      <MLEvalFormModal
        open={isMlEditModalOpen}
        onClose={() => setIsMlEditModalOpen(false)}
        onSubmit={handleMlEditSubmit}
        isLoading={createMlEvalMutation.isPending}
        initialName={evalName}
        initialType={evalData.eval_type}
        initialConfig={evalData.config as unknown as Record<string, unknown>}
      />

      <ImpactedCEsDialog
        open={isImpactedCEsDialogOpen}
        onClose={() => setIsImpactedCEsDialogOpen(false)}
        impactedCEs={impactedCEs}
        newVersion={impactedCEsNewVersion}
        evalName={evalName}
      />
    </Box>
  );
};

export default EvalDetailView;
