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
import React, { useState } from "react";

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
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const createConfig = useCreateRagConfig();
  const createVersion = useCreateRagVersion();

  const { data } = useRagSearchSettings(taskId);
  const existingConfigs = data?.rag_provider_setting_configurations ?? [];
  const existingConfig = existingConfigs.find((c) => c.name === name);

  const handleSave = async () => {
    if (!name.trim()) {
      showSnackbar("Configuration name is required", "error");
      return;
    }

    const apiSettings = buildApiSettings(selectedCollection, searchMethod, settings);

    try {
      if (existingConfig) {
        // Create new version
        const response = await createVersion.mutateAsync({
          configId: existingConfig.id,
          request: {
            settings: apiSettings,
            tags,
          },
        });
        showSnackbar(`Created version ${response.version_number} of "${name}"`, "success");
        if (onSaveSuccess) {
          onSaveSuccess(existingConfig.id, response.version_number);
        }
      } else {
        // Create new config
        const response = await createConfig.mutateAsync({
          taskId,
          request: {
            name,
            description: description || null,
            rag_provider_id: currentProviderId,
            settings: apiSettings,
            tags,
          },
        });
        showSnackbar(`Saved configuration "${name}"`, "success");
        if (onSaveSuccess) {
          onSaveSuccess(response.id, response.latest_version_number);
        }
      }
      setOpen(false);
      setName("");
      setDescription("");
      setTags([]);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      const apiError = error as { response?: { data?: { detail?: string } } };
      const detailMessage = apiError?.response?.data?.detail || errorMessage;
      showSnackbar(`Failed to save configuration: ${detailMessage}`, "error");
    }
  };

  const handleClose = () => {
    setOpen(false);
    setName("");
    setDescription("");
    setTags([]);
  };

  React.useEffect(() => {
    if (open) {
      if (currentConfigName) {
        setName(currentConfigName);
      } else {
        setName("");
      }
    }
  }, [open, currentConfigName]);

  return (
    <>
      <Dialog open={open} onClose={handleClose} fullWidth>
        <DialogTitle>Save Configuration</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {existingConfig
              ? `Saving with an existing name will create version ${existingConfig.latest_version_number + 1}.`
              : "Create a new search configuration with all current settings."}
          </DialogContentText>
          <div className="space-y-3 pt-2">
            <Autocomplete
              freeSolo
              options={existingConfigs.map((c) => c.name)}
              value={name}
              onInputChange={(_e, newValue) => setName(newValue)}
              renderInput={(params) => <TextField {...params} label="Configuration Name" autoFocus required fullWidth />}
            />
            <TextField
              label="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              multiline
              rows={2}
              fullWidth
            />
            <Autocomplete
              multiple
              freeSolo
              options={[]}
              value={tags}
              onChange={(_e, newValue) => setTags(newValue)}
              renderTags={(value, getTagProps) =>
                value.map((option, index) => {
                  const { key, ...tagProps } = getTagProps({ index });
                  return <Chip key={key} label={option} variant="outlined" {...tagProps} />;
                })
              }
              renderInput={(params) => <TextField {...params} label="Tags" placeholder="Add tags..." />}
            />
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={createConfig.isPending || createVersion.isPending}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
