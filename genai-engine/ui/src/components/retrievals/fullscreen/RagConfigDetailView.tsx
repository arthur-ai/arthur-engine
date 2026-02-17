import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";

import type { ApiSearchSettings } from "../types";
import { mapApiSettingsToLocal, getMethodFromApiKind } from "../utils/ragSettingsUtils";

import { RagConfigEditModal } from "./RagConfigEditModal";

import { useUpdateVersionTags } from "@/hooks/rag-search-settings/useUpdateVersionTags";
import type { RagProviderCollectionResponse, RagSearchSettingConfigurationResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

interface RagConfigDetailViewProps {
  config: RagSearchSettingConfigurationResponse | null;
  settings: ApiSearchSettings | null;
  collection: RagProviderCollectionResponse | null;
  versionNumber: number | null;
  versionTags: string[];
  latestVersion: number | null;
  isLoading: boolean;
  error: Error | null;
  onClose: () => void;
  onRefetch?: (newVersion?: number) => void;
}

const SEARCH_METHOD_LABELS: Record<string, string> = {
  hybrid_search: "Hybrid Search",
  vector_similarity_text_search: "Near Text (Vector)",
  keyword_search: "BM25 (Keyword)",
};

const RagConfigDetailView = ({
  config,
  settings,
  collection,
  versionNumber,
  versionTags,
  latestVersion,
  isLoading,
  error,
  onClose,
  onRefetch,
}: RagConfigDetailViewProps) => {
  const [tagAnchorEl, setTagAnchorEl] = useState<HTMLButtonElement | null>(null);
  const [newTag, setNewTag] = useState("");
  const [tagError, setTagError] = useState("");
  const [editModalKey, setEditModalKey] = useState(0);
  const isEditModalOpen = editModalKey > 0;

  const updateTagsMutation = useUpdateVersionTags();

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
    if (!newTag.trim()) {
      setTagError("Please enter a tag");
      return;
    }

    if (newTag.trim().toLowerCase() === "latest") {
      setTagError("'latest' is a reserved keyword and cannot be used as a tag");
      return;
    }

    if (versionTags.includes(newTag.trim())) {
      setTagError("This tag already exists");
      return;
    }

    if (!config?.id || versionNumber === null) return;

    try {
      await updateTagsMutation.mutateAsync({
        configId: config.id,
        versionNumber,
        tags: [...versionTags, newTag.trim()],
      });

      setTagAnchorEl(null);
      setNewTag("");
      setTagError("");
      onRefetch?.();
    } catch (err) {
      setTagError(err instanceof Error ? err.message : "Failed to add tag");
    }
  }, [newTag, versionTags, config?.id, versionNumber, updateTagsMutation, onRefetch]);

  const handleDeleteTag = useCallback(
    async (tag: string) => {
      if (!config?.id || versionNumber === null) return;

      try {
        await updateTagsMutation.mutateAsync({
          configId: config.id,
          versionNumber,
          tags: versionTags.filter((t) => t !== tag),
        });
        onRefetch?.();
      } catch (err) {
        console.error("Failed to delete tag:", err);
      }
    },
    [config?.id, versionNumber, versionTags, updateTagsMutation, onRefetch]
  );

  const handleEditClick = useCallback(() => {
    setEditModalKey((prev) => prev + 1);
  }, []);

  const handleEditModalClose = useCallback(() => {
    setEditModalKey(0);
  }, []);

  const handleEditSuccess = useCallback(
    (newVersionNumber: number) => {
      setEditModalKey(0);
      onRefetch?.(newVersionNumber);
    },
    [onRefetch]
  );

  const tagPopoverOpen = Boolean(tagAnchorEl);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Error loading configuration: {error.message}</Alert>
      </Box>
    );
  }

  if (!config || !settings) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No configuration data available</Alert>
      </Box>
    );
  }

  const localSettings = mapApiSettingsToLocal(settings);
  const searchMethodLabel = SEARCH_METHOD_LABELS[settings.search_kind ?? ""] ?? settings.search_kind ?? "Unknown";
  const searchMethod = getMethodFromApiKind(settings.search_kind ?? "hybrid_search");

  return (
    <Box sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", mb: 2, flexShrink: 0 }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, flex: 1 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              {config.name}
            </Typography>
            {versionNumber !== null && <Chip label={`Version ${versionNumber}`} size="small" sx={{ height: 24 }} />}
            {versionNumber !== null && versionNumber === latestVersion && <Chip label="Latest" size="small" color="default" sx={{ height: 24 }} />}
            {versionTags.length > 0 && (
              <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                {versionTags.map((tag) => (
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
            {versionNumber !== null && (
              <IconButton size="small" onClick={handleAddTagClick} aria-label="Add tag">
                <LocalOfferIcon fontSize="small" />
              </IconButton>
            )}
          </Box>

          {/* Metadata row */}
          <Box sx={{ display: "flex", gap: 3, flexWrap: "wrap", alignItems: "center" }}>
            {config.description && (
              <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400 }}>
                {config.description}
              </Typography>
            )}
            <Box sx={{ display: "flex", gap: 0.5, alignItems: "baseline" }}>
              <Typography variant="caption" color="text.secondary">
                Created:
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                {formatDate(new Date(config.created_at).toISOString())}
              </Typography>
            </Box>
          </Box>
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={handleEditClick} sx={{ minWidth: 120 }}>
            New Version
          </Button>
          <IconButton onClick={onClose} aria-label="Close">
            <CloseIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Settings Content */}
      <Paper sx={{ p: 3, flex: 1, minHeight: 0, overflow: "auto" }}>
        <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
          Search Configuration
        </Typography>

        <Stack spacing={3}>
          {/* Search Method */}
          <Box>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 0.5 }}>
              Search Method
            </Typography>
            <Chip label={searchMethodLabel} color="primary" variant="outlined" />
          </Box>

          <Divider />

          {/* Connection Info */}
          <Box>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5 }}>
              Connection
            </Typography>
            <Stack spacing={1.5}>
              <SettingRow label="Collection" value={settings.collection_name ?? "-"} />
              {collection?.description && <SettingRow label="Collection Description" value={collection.description} />}
            </Stack>
          </Box>

          <Divider />

          {/* Search Parameters */}
          <Box>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5 }}>
              Parameters
            </Typography>
            <Stack spacing={1.5}>
              <SettingRow label="Result Limit" value={String(localSettings.limit)} />
              {(searchMethod === "nearText" || searchMethod === "hybrid") && (
                <SettingRow label="Distance Threshold" value={localSettings.distance.toFixed(2)} />
              )}
              {searchMethod === "hybrid" && <SettingRow label="Alpha" value={localSettings.alpha.toFixed(2)} />}
              <SettingRow label="Include Vector" value={localSettings.includeVector ? "Yes" : "No"} />
              <SettingRow label="Include Metadata" value={localSettings.includeMetadata ? "Yes" : "No"} />
            </Stack>
          </Box>

          {/* Return metadata fields */}
          {settings.return_metadata && Array.isArray(settings.return_metadata) && settings.return_metadata.length > 0 && (
            <>
              <Divider />
              <Box>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1.5 }}>
                  Return Metadata Fields
                </Typography>
                <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                  {settings.return_metadata.map((field: string) => (
                    <Chip key={field} label={field} size="small" variant="outlined" />
                  ))}
                </Box>
              </Box>
            </>
          )}
        </Stack>
      </Paper>

      {/* Tag Popover */}
      <Popover
        open={tagPopoverOpen}
        anchorEl={tagAnchorEl}
        onClose={handleAddTagClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
      >
        <Box sx={{ p: 2, minWidth: 300 }}>
          <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 600 }}>
            Version Tags
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: "block" }}>
            Tags to easily identify your configuration versions.
          </Typography>

          <Divider sx={{ mb: 2 }} />

          <Typography variant="subtitle1" sx={{ mb: 0.5, fontWeight: 600 }}>
            Add Tag
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: "block" }}>
            Add a tag to this version
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
            <Button size="small" onClick={handleAddTagClose} disabled={updateTagsMutation.isPending}>
              Cancel
            </Button>
            <Button
              size="small"
              onClick={handleAddTagConfirm}
              variant="contained"
              disabled={updateTagsMutation.isPending}
              startIcon={updateTagsMutation.isPending ? <CircularProgress size={14} /> : <AddIcon />}
            >
              {updateTagsMutation.isPending ? "Adding..." : "Save"}
            </Button>
          </Box>
        </Box>
      </Popover>

      {/* Edit Modal (Create New Version) -- key forces remount so initial state is fresh */}
      {config && (
        <RagConfigEditModal
          key={editModalKey}
          open={isEditModalOpen}
          onClose={handleEditModalClose}
          configId={config.id}
          configName={config.name}
          providerId={config.rag_provider_id ?? null}
          currentSettings={settings}
          onSuccess={handleEditSuccess}
        />
      )}
    </Box>
  );
};

interface SettingRowProps {
  label: string;
  value: string;
}

const SettingRow: React.FC<SettingRowProps> = ({ label, value }) => (
  <Box sx={{ display: "flex", alignItems: "baseline", gap: 1 }}>
    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 160 }}>
      {label}:
    </Typography>
    <Typography variant="body2" sx={{ fontWeight: 500 }}>
      {value}
    </Typography>
  </Box>
);

export default RagConfigDetailView;
