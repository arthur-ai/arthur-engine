import { Add, Storage } from "@mui/icons-material";
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
import { useForm } from "@tanstack/react-form";
import React, { useCallback, useEffect, useState } from "react";

import { SearchSettings } from "./SearchSettings";
import type { SearchMethod, SearchSettings as SearchSettingsType } from "./types";
import { buildApiSearchSettings } from "./utils/ragSettingsUtils";

import { RagProviderFormModal } from "@/components/rag/RagProviderFormModal";
import { useRagCollections } from "@/hooks/rag/useRagCollections";
import { useRagProviders } from "@/hooks/rag/useRagProviders";
import { useCreateRagConfig } from "@/hooks/rag-search-settings/useCreateRagConfig";
import useSnackbar from "@/hooks/useSnackbar";
import type { RagProviderCollectionResponse } from "@/lib/api-client/api-client";

interface CreateRagConfigurationModalProps {
  open: boolean;
  onClose: () => void;
  taskId: string;
  onSuccess?: () => void;
}

const DEFAULT_SEARCH_SETTINGS: SearchSettingsType = {
  limit: 10,
  distance: 0.3,
  alpha: 0.5,
  includeVector: false,
  includeMetadata: true,
};

const DEFAULT_FORM_VALUES = {
  name: "",
  description: "",
  tags: [] as string[],
};

export const CreateRagConfigurationModal: React.FC<CreateRagConfigurationModalProps> = ({ open, onClose, taskId, onSuccess }) => {
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();
  const createConfig = useCreateRagConfig();

  // Data fetching
  const { providers, isLoading: isLoadingProviders, refetch: refetchProviders } = useRagProviders(taskId);

  // Local state for configuration builder
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [selectedCollection, setSelectedCollection] = useState<RagProviderCollectionResponse | null>(null);
  const [searchMethod, setSearchMethod] = useState<SearchMethod>("hybrid");
  const [searchSettings, setSearchSettings] = useState<SearchSettingsType>(DEFAULT_SEARCH_SETTINGS);
  const [tagInputValue, setTagInputValue] = useState("");
  const [createProviderModalOpen, setCreateProviderModalOpen] = useState(false);

  // Fetch collections for selected provider
  const { collections, isLoading: isLoadingCollections } = useRagCollections(selectedProviderId || undefined);

  // Reset all local state to defaults
  const resetLocalState = useCallback((defaultProviderId = "") => {
    setSelectedProviderId(defaultProviderId);
    setSelectedCollection(null);
    setSearchMethod("hybrid");
    setSearchSettings(DEFAULT_SEARCH_SETTINGS);
    setTagInputValue("");
  }, []);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      const defaultProviderId = providers.length > 0 ? providers[0].id : "";
      resetLocalState(defaultProviderId);
    }
  }, [open, providers, resetLocalState]);

  // Auto-select first collection when collections load for a new provider
  useEffect(() => {
    if (collections.length > 0 && !selectedCollection) {
      setSelectedCollection(collections[0]);
    } else if (collections.length === 0) {
      setSelectedCollection(null);
    }
  }, [collections, selectedCollection]);

  const form = useForm({
    defaultValues: DEFAULT_FORM_VALUES,
    onSubmit: async ({ value, formApi }) => {
      const trimmedName = value.name.trim();
      if (!trimmedName || !selectedProviderId || !selectedCollection) {
        return;
      }

      const apiSettings = buildApiSearchSettings(selectedCollection.identifier, searchMethod, searchSettings);

      try {
        await createConfig.mutateAsync({
          taskId,
          request: {
            name: trimmedName,
            description: value.description || null,
            rag_provider_id: selectedProviderId,
            settings: apiSettings,
            tags: value.tags,
          },
        });

        showSnackbar(`Created configuration "${trimmedName}"`, "success");
        formApi.reset(DEFAULT_FORM_VALUES);
        onSuccess?.();
        onClose();
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        const apiError = error as { response?: { data?: { detail?: string } } };
        const detailMessage = apiError?.response?.data?.detail || errorMessage;
        showSnackbar(`Failed to create configuration: ${detailMessage}`, "error");
      }
    },
  });

  const handleClose = useCallback(() => {
    form.reset(DEFAULT_FORM_VALUES);
    resetLocalState();
    onClose();
  }, [form, resetLocalState, onClose]);

  const handleProviderChange = useCallback((e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedProviderId(e.target.value);
    setSelectedCollection(null);
  }, []);

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

  const handleCreateProviderSuccess = useCallback(() => {
    refetchProviders();
    setCreateProviderModalOpen(false);
  }, [refetchProviders]);

  // Derived state
  const isSaving = createConfig.isPending;
  const hasNoProviders = !isLoadingProviders && providers.length === 0;
  const hasRequiredSelections = Boolean(selectedProviderId && selectedCollection);

  return (
    <>
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            form.handleSubmit();
          }}
        >
          <DialogTitle>Create RAG Configuration</DialogTitle>
          <DialogContent>
            {isLoadingProviders ? (
              <Box className="flex justify-center items-center py-8">
                <CircularProgress />
              </Box>
            ) : hasNoProviders ? (
              <Box className="py-6 text-center">
                <Storage sx={{ fontSize: 48, color: "text.disabled", mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No RAG Providers Found
                </Typography>
                <Typography variant="body2" color="text.secondary" className="mb-4">
                  You need to create a RAG provider connection before you can create a configuration. A provider connects to your vector database
                  (e.g., Weaviate).
                </Typography>
                <Button variant="contained" startIcon={<Add />} onClick={() => setCreateProviderModalOpen(true)}>
                  Create Provider
                </Button>
              </Box>
            ) : (
              <Box className="space-y-4 pt-2">
                {/* Provider Selection */}
                <Box>
                  <Box className="flex items-center justify-between mb-1">
                    <label htmlFor="provider-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Provider
                    </label>
                    <Button size="small" startIcon={<Add />} onClick={() => setCreateProviderModalOpen(true)} sx={{ textTransform: "none" }}>
                      Add Provider
                    </Button>
                  </Box>
                  <select
                    id="provider-select"
                    value={selectedProviderId}
                    onChange={handleProviderChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Select a provider</option>
                    {providers.map((provider) => (
                      <option key={provider.id} value={provider.id}>
                        {provider.name}
                      </option>
                    ))}
                  </select>
                </Box>

                {/* Collection Selection */}
                {selectedProviderId && (
                  <Box>
                    <label htmlFor="collection-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Collection
                    </label>
                    <Box className="flex items-center gap-2">
                      <select
                        id="collection-select"
                        value={selectedCollection?.identifier ?? ""}
                        onChange={handleCollectionChange}
                        disabled={isLoadingCollections}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800"
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
                )}

                {/* Search Method */}
                {hasRequiredSelections && (
                  <Box>
                    <label htmlFor="method-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Search Method
                    </label>
                    <select
                      id="method-select"
                      value={searchMethod}
                      onChange={handleMethodChange}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="nearText">Near Text (Vector)</option>
                      <option value="bm25">BM25 (Keyword)</option>
                      <option value="hybrid">Hybrid</option>
                    </select>
                  </Box>
                )}

                {/* Search Settings */}
                {hasRequiredSelections && (
                  <Box>
                    <Typography variant="subtitle2" className="text-gray-700 dark:text-gray-300 mb-2">
                      Search Settings
                    </Typography>
                    <Box className="bg-gray-50 dark:bg-gray-800 p-3 rounded-md">
                      <SearchSettings
                        searchMethod={searchMethod}
                        settings={searchSettings}
                        onSettingsChange={setSearchSettings}
                        isExecuting={false}
                      />
                    </Box>
                  </Box>
                )}

                <Divider />

                {/* Configuration Details */}
                <form.Field
                  name="name"
                  validators={{
                    onChange: ({ value }) => (!value.trim() ? "Configuration name is required" : undefined),
                  }}
                >
                  {(field) => (
                    <TextField
                      label="Configuration Name"
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      required
                      fullWidth
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]}
                      placeholder="My RAG Configuration"
                    />
                  )}
                </form.Field>

                <form.Field name="description">
                  {(field) => (
                    <TextField
                      label="Description (optional)"
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      multiline
                      rows={2}
                      fullWidth
                      placeholder="Describe what this configuration is for..."
                    />
                  )}
                </form.Field>

                <form.Field name="tags">
                  {(field) => (
                    <Autocomplete
                      multiple
                      freeSolo
                      options={[]}
                      value={field.state.value}
                      inputValue={tagInputValue}
                      onInputChange={(_e, newInputValue) => setTagInputValue(newInputValue)}
                      onChange={(_e, newValue) => {
                        field.handleChange(newValue);
                        setTagInputValue("");
                      }}
                      onBlur={() => {
                        const trimmed = tagInputValue.trim();
                        if (trimmed && !field.state.value.includes(trimmed)) {
                          field.handleChange([...field.state.value, trimmed]);
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
                  )}
                </form.Field>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose} disabled={isSaving}>
              Cancel
            </Button>
            {!hasNoProviders && (
              <form.Subscribe selector={(state) => state.values.name}>
                {(name) => (
                  <Button type="submit" variant="contained" disabled={!name.trim() || !hasRequiredSelections || isSaving}>
                    {isSaving ? "Creating..." : "Create Configuration"}
                  </Button>
                )}
              </form.Subscribe>
            )}
          </DialogActions>
        </form>
      </Dialog>

      <RagProviderFormModal
        open={createProviderModalOpen}
        onClose={() => setCreateProviderModalOpen(false)}
        onSuccess={handleCreateProviderSuccess}
        taskId={taskId}
        mode="create"
      />

      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
