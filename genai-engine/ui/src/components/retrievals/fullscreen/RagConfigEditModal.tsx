import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React, { useCallback, useState } from "react";

import { SearchSettings } from "../SearchSettings";
import type { ApiSearchSettings, SearchMethod, SearchSettings as SearchSettingsType } from "../types";
import { buildApiSearchSettings, getMethodFromApiKind, mapApiSettingsToLocal } from "../utils/ragSettingsUtils";

import { useRagCollections } from "@/hooks/rag/useRagCollections";
import { useCreateRagVersion } from "@/hooks/rag-search-settings/useCreateRagVersion";
import useSnackbar from "@/hooks/useSnackbar";
import type { RagProviderCollectionResponse } from "@/lib/api-client/api-client";

interface RagConfigEditModalProps {
  open: boolean;
  onClose: () => void;
  configId: string;
  configName: string;
  providerId: string | null;
  currentSettings: ApiSearchSettings | null;
  onSuccess?: (newVersionNumber: number) => void;
}

export const RagConfigEditModal: React.FC<RagConfigEditModalProps> = ({
  open,
  onClose,
  configId,
  configName,
  providerId,
  currentSettings,
  onSuccess,
}) => {
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();
  const createVersion = useCreateRagVersion();

  const initialMethod = getMethodFromApiKind(currentSettings?.search_kind ?? "hybrid_search");
  const initialSettings: SearchSettingsType = currentSettings
    ? mapApiSettingsToLocal(currentSettings)
    : { limit: 10, distance: 0.3, alpha: 0.5, includeVector: false, includeMetadata: true };

  const [searchMethod, setSearchMethod] = useState<SearchMethod>(initialMethod);
  const [searchSettings, setSearchSettings] = useState<SearchSettingsType>(initialSettings);
  const [selectedCollection, setSelectedCollection] = useState<RagProviderCollectionResponse | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInputValue, setTagInputValue] = useState("");

  const { collections, isLoading: isLoadingCollections } = useRagCollections(providerId || undefined);

  // Derive the effective collection: user selection takes priority, otherwise match from loaded collections
  const effectiveCollection =
    selectedCollection ??
    (collections.length > 0 && currentSettings?.collection_name
      ? (collections.find((c) => c.identifier === currentSettings.collection_name) ?? collections[0])
      : null);

  const handleSubmit = useCallback(async () => {
    if (!effectiveCollection) return;

    const apiSettings = buildApiSearchSettings(effectiveCollection.identifier, searchMethod, searchSettings);

    try {
      const result = await createVersion.mutateAsync({
        configId,
        request: {
          settings: apiSettings,
          tags: tags.length > 0 ? tags : undefined,
        },
      });

      showSnackbar(`Created version ${result.version_number} for "${configName}"`, "success");
      onSuccess?.(result.version_number);
      onClose();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      const apiError = error as { response?: { data?: { detail?: string } } };
      const detailMessage = apiError?.response?.data?.detail || errorMessage;
      showSnackbar(`Failed to create version: ${detailMessage}`, "error");
    }
  }, [effectiveCollection, searchMethod, searchSettings, tags, configId, configName, createVersion, showSnackbar, onSuccess, onClose]);

  const handleCollectionChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const collection = collections.find((c) => c.identifier === e.target.value);
      setSelectedCollection(collection ?? null);
    },
    [collections]
  );

  const handleMethodChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setSearchMethod(e.target.value as SearchMethod);
  }, []);

  const isSaving = createVersion.isPending;

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>New Version for &ldquo;{configName}&rdquo;</DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}>
            {/* Collection Selection */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Collection
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <select
                  value={effectiveCollection?.identifier ?? ""}
                  onChange={handleCollectionChange}
                  disabled={isLoadingCollections}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: 4,
                    border: "1px solid #ccc",
                    fontSize: "0.875rem",
                  }}
                >
                  {isLoadingCollections ? (
                    <option value="">Loading collections...</option>
                  ) : collections.length === 0 ? (
                    <option value="">No collections available</option>
                  ) : (
                    <>
                      <option value="">Select a collection</option>
                      {collections.map((collection) => (
                        <option key={collection.identifier} value={collection.identifier}>
                          {collection.identifier}
                        </option>
                      ))}
                    </>
                  )}
                </select>
                {isLoadingCollections && <CircularProgress size={20} />}
              </Box>
            </Box>

            {/* Search Method */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Search Method
              </Typography>
              <select
                value={searchMethod}
                onChange={handleMethodChange}
                style={{
                  width: "100%",
                  padding: "8px 12px",
                  borderRadius: 4,
                  border: "1px solid #ccc",
                  fontSize: "0.875rem",
                }}
              >
                <option value="nearText">Near Text (Vector)</option>
                <option value="bm25">BM25 (Keyword)</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </Box>

            {/* Search Settings */}
            <Box>
              <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                Search Settings
              </Typography>
              <Box sx={{ p: 2, bgcolor: "action.hover", borderRadius: 1 }}>
                <SearchSettings searchMethod={searchMethod} settings={searchSettings} onSettingsChange={setSearchSettings} isExecuting={false} />
              </Box>
            </Box>

            <Divider />

            {/* Tags */}
            <Autocomplete
              multiple
              freeSolo
              options={[]}
              value={tags}
              inputValue={tagInputValue}
              onInputChange={(_e, newInputValue) => setTagInputValue(newInputValue)}
              onChange={(_e, newValue) => {
                setTags(newValue);
                setTagInputValue("");
              }}
              onBlur={() => {
                const trimmed = tagInputValue.trim();
                if (trimmed && !tags.includes(trimmed)) {
                  setTags([...tags, trimmed]);
                }
                setTagInputValue("");
              }}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => {
                  const { key, ...tagProps } = getTagProps({ index });
                  return <Chip key={key} label={option} variant="outlined" size="small" {...tagProps} />;
                })
              }
              renderInput={(params) => <TextField {...params} label="Tags (optional)" placeholder="Add tags..." />}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleSubmit} disabled={!effectiveCollection || isSaving}>
            {isSaving ? "Creating..." : "Create Version"}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
