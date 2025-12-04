import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import { useForm, useStore } from "@tanstack/react-form";
import React, { useEffect } from "react";

import type { SearchMethod, SearchSettings } from "./types";

import { useCreateRagConfig } from "@/hooks/rag-search-settings/useCreateRagConfig";
import { useCreateRagVersion } from "@/hooks/rag-search-settings/useCreateRagVersion";
import { useRagSearchSettings } from "@/hooks/rag-search-settings/useRagSearchSettings";
import useSnackbar from "@/hooks/useSnackbar";
import type {
  RagProviderCollectionResponse,
  WeaviateHybridSearchSettingsConfigurationRequest,
  WeaviateKeywordSearchSettingsConfigurationRequest,
  WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
} from "@/lib/api-client/api-client";

interface SaveRagConfigDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  currentConfigName: string | null;
  currentProviderId: string;
  selectedCollection: RagProviderCollectionResponse;
  searchMethod: SearchMethod;
  settings: SearchSettings;
  taskId: string;
  onSaveSuccess?: (configId: string, versionNumber: number) => void;
}

interface SaveRagConfigFormValues {
  name: string;
  description: string;
  tags: string[];
}

function buildApiSettings(
  collection: RagProviderCollectionResponse,
  method: SearchMethod,
  settings: SearchSettings
):
  | WeaviateHybridSearchSettingsConfigurationRequest
  | WeaviateKeywordSearchSettingsConfigurationRequest
  | WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest {
  const base = {
    collection_name: collection.identifier,
    limit: settings.limit,
    include_vector: settings.includeVector,
    return_properties: settings.includeMetadata ? undefined : [],
    return_metadata: ["distance", "certainty", "score", "explain_score"],
  };

  if (method === "nearText") {
    return {
      ...base,
      certainty: 1 - settings.distance,
    } as WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest;
  } else if (method === "bm25") {
    return base as WeaviateKeywordSearchSettingsConfigurationRequest;
  } else {
    // hybrid
    return {
      ...base,
      alpha: settings.alpha,
      certainty: 1 - settings.distance,
    } as WeaviateHybridSearchSettingsConfigurationRequest;
  }
}

const blankValues: SaveRagConfigFormValues = {
  name: "",
  description: "",
  tags: [],
};

export const SaveRagConfigDialog: React.FC<SaveRagConfigDialogProps> = ({
  open,
  setOpen,
  currentConfigName,
  currentProviderId,
  selectedCollection,
  searchMethod,
  settings,
  taskId,
  onSaveSuccess,
}) => {
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const createConfig = useCreateRagConfig();
  const createVersion = useCreateRagVersion();

  const { data } = useRagSearchSettings(taskId);
  const existingConfigs = data?.rag_provider_setting_configurations ?? [];

  const form = useForm({
    defaultValues: {
      ...blankValues,
      name: currentConfigName ?? "",
    },
    onSubmit: async ({ value, formApi }) => {
      const trimmedName = value.name.trim();
      if (!trimmedName) {
        return;
      }

      const apiSettings = buildApiSettings(selectedCollection, searchMethod, settings);
      const matchedConfig = existingConfigs.find((c) => c.name === trimmedName);

      try {
        if (matchedConfig) {
          const response = await createVersion.mutateAsync({
            configId: matchedConfig.id,
            request: {
              settings: apiSettings,
              tags: value.tags,
            },
          });
          showSnackbar(`Created version ${response.version_number} of "${trimmedName}"`, "success");
          if (onSaveSuccess) {
            onSaveSuccess(matchedConfig.id, response.version_number);
          }
        } else {
          const response = await createConfig.mutateAsync({
            taskId,
            request: {
              name: trimmedName,
              description: value.description || null,
              rag_provider_id: currentProviderId,
              settings: apiSettings,
              tags: value.tags,
            },
          });
          showSnackbar(`Saved configuration "${trimmedName}"`, "success");
          if (onSaveSuccess) {
            onSaveSuccess(response.id, response.latest_version_number);
          }
        }

        setOpen(false);
        formApi.reset(blankValues);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        const apiError = error as { response?: { data?: { detail?: string } } };
        const detailMessage = apiError?.response?.data?.detail || errorMessage;
        showSnackbar(`Failed to save configuration: ${detailMessage}`, "error");
      }
    },
  });

  const formValues = useStore(form.store, (state) => state.values);
  const existingConfig = existingConfigs.find((c) => c.name === formValues.name);
  const isSaving = createConfig.isPending || createVersion.isPending;

  const handleClose = () => {
    setOpen(false);
    form.reset(blankValues);
  };

  useEffect(() => {
    if (open) {
      form.reset({
        ...blankValues,
        name: currentConfigName ?? "",
      });
    }
  }, [open, currentConfigName, form]);

  return (
    <>
      <Dialog open={open} onClose={handleClose} fullWidth>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            form.handleSubmit();
          }}
        >
          <DialogTitle>Save Configuration</DialogTitle>
          <DialogContent>
            <DialogContentText>
              {existingConfig
                ? `Saving with an existing name will create version ${existingConfig.latest_version_number + 1}.`
                : "Create a new search configuration with all current settings."}
            </DialogContentText>
            <div className="space-y-3 pt-2">
              <form.Field
                name="name"
                validators={{
                  onChange: ({ value }) => (!value.trim() ? "Configuration name is required" : undefined),
                }}
              >
                {(field) => (
                  <Autocomplete
                    freeSolo
                    options={existingConfigs.map((c) => c.name)}
                    value={field.state.value}
                    onInputChange={(_e, newValue) => field.handleChange(newValue)}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Configuration Name"
                        autoFocus
                        required
                        fullWidth
                        error={field.state.meta.errors.length > 0}
                        helperText={field.state.meta.errors[0]}
                      />
                    )}
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
                    onChange={(_e, newValue) => field.handleChange(newValue)}
                    renderTags={(value, getTagProps) =>
                      value.map((option, index) => {
                        const { key, ...tagProps } = getTagProps({ index });
                        return <Chip key={key} label={option} variant="outlined" {...tagProps} />;
                      })
                    }
                    renderInput={(params) => <TextField {...params} label="Tags" placeholder="Add tags..." />}
                  />
                )}
              </form.Field>
            </div>
          </DialogContent>
          <DialogActions>
            <Button onClick={handleClose}>Cancel</Button>
            <form.Subscribe selector={(state) => state.canSubmit}>
              {(canSubmit) => (
                <Button type="submit" variant="contained" disabled={!canSubmit || isSaving}>
                  Save
                </Button>
              )}
            </form.Subscribe>
          </DialogActions>
        </form>
      </Dialog>
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
