import {
  Alert,
  AlertTitle,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import React, { useCallback, useEffect, useState } from "react";

import type { GenerationConfig } from "./types";

import { useApi } from "@/hooks/useApi";
import type { DatasetVersionRowResponse, ModelProvider, ModelProviderResponse, SyntheticDataPromptStatus } from "@/lib/api-client/api-client";

interface SyntheticDataConfigFormProps {
  columns: string[];
  existingRowsSample: DatasetVersionRowResponse[];
  onSubmit: (config: GenerationConfig) => void;
  onCancel: () => void;
  isLoading: boolean;
}

interface ColumnDescription {
  columnName: string;
  description: string;
}

export const SyntheticDataConfigForm: React.FC<SyntheticDataConfigFormProps> = ({
  columns,
  existingRowsSample: _existingRowsSample,
  onSubmit,
  onCancel,
  isLoading,
}) => {
  const api = useApi();

  // Form state
  const [datasetPurpose, setDatasetPurpose] = useState("");
  const [columnDescriptions, setColumnDescriptions] = useState<ColumnDescription[]>(columns.map((col) => ({ columnName: col, description: "" })));
  const [numRows, setNumRows] = useState(10);
  const [modelProvider, setModelProvider] = useState<ModelProvider | null>(null);
  const [modelName, setModelName] = useState<string | null>(null);
  const [editExisting, setEditExisting] = useState(false);

  // Prompt status state (placeholder vs real model)
  const [promptStatus, setPromptStatus] = useState<SyntheticDataPromptStatus | null>(null);

  // Provider/model loading state
  const [providers, setProviders] = useState<ModelProviderResponse[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load providers on mount
  useEffect(() => {
    const fetchProviders = async () => {
      if (!api) return;

      try {
        setIsLoadingProviders(true);
        const response = await api.api.getModelProvidersApiV1ModelProvidersGet();
        const enabledProviders = (response.data.providers || []).filter((p) => p.enabled);
        setProviders(enabledProviders);

        // Auto-select first enabled provider
        if (enabledProviders.length > 0) {
          setModelProvider(enabledProviders[0].provider);
        }
      } catch (err) {
        console.error("Failed to fetch model providers:", err);
        setError("Failed to load model providers");
      } finally {
        setIsLoadingProviders(false);
      }
    };

    fetchProviders();
  }, [api]);

  // Fetch prompt status on mount; pre-populate model if a real model is stored
  useEffect(() => {
    if (!api) return;
    api.api
      .getSyntheticDataPromptStatusApiV2DatasetsSyntheticDataPromptStatusGet()
      .then((res) => {
        setPromptStatus(res.data);
        if (!res.data.is_placeholder) {
          setModelProvider(res.data.model_provider as ModelProvider);
          setModelName(res.data.model_name);
        }
      })
      .catch(() => {}); // best-effort; don't block the form
  }, [api]);

  // Load models when provider changes
  useEffect(() => {
    const fetchModels = async () => {
      if (!api || !modelProvider) {
        setAvailableModels([]);
        return;
      }

      try {
        setIsLoadingModels(true);
        setModelName(null);
        const response = await api.api.getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet(modelProvider);
        setAvailableModels(response.data.available_models || []);
      } catch (err) {
        console.error("Failed to fetch available models:", err);
        setAvailableModels([]);
      } finally {
        setIsLoadingModels(false);
      }
    };

    fetchModels();
  }, [api, modelProvider]);

  const handleColumnDescriptionChange = useCallback((columnName: string, description: string) => {
    setColumnDescriptions((prev) => prev.map((col) => (col.columnName === columnName ? { ...col, description } : col)));
  }, []);

  // When the stored prompt already has a real model, the selection UI is hidden
  // and the form should use those values instead of the editable state (which can
  // race with the provider-change effect below and end up cleared).
  const usesStoredModel = promptStatus?.is_placeholder === false;
  const effectiveModelProvider = usesStoredModel ? (promptStatus.model_provider as ModelProvider) : modelProvider;
  const effectiveModelName = usesStoredModel ? promptStatus.model_name : modelName;

  const handleSubmit = useCallback(() => {
    if (!effectiveModelProvider || !effectiveModelName) return;

    onSubmit({
      datasetPurpose,
      columnDescriptions,
      numRows,
      modelProvider: effectiveModelProvider,
      modelName: effectiveModelName,
      editExisting,
    });
  }, [datasetPurpose, columnDescriptions, numRows, effectiveModelProvider, effectiveModelName, editExisting, onSubmit]);

  const enabledProviders = providers.filter((p) => p.enabled);
  const canSubmit =
    datasetPurpose.trim() && effectiveModelProvider && effectiveModelName && columnDescriptions.every((col) => col.description.trim());

  // Only block on providers loading when the user needs to pick a model (placeholder case)
  // When promptStatus is not yet loaded, wait for it first
  if (isLoadingProviders && promptStatus?.is_placeholder !== false) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (promptStatus?.is_placeholder && enabledProviders.length === 0) {
    return (
      <Box sx={{ py: 2 }}>
        <Alert severity="warning">
          No model providers are configured. Please configure at least one model provider in Settings to use synthetic data generation.
        </Alert>
        <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
          <Button onClick={onCancel}>Close</Button>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 3, py: 1 }}>
      {error && <Alert severity="error">{error}</Alert>}

      {promptStatus?.is_placeholder && (
        <Alert severity="warning">
          <AlertTitle>Prompts not configured</AlertTitle>
          The Synthetic Dataset Generation system prompts are currently using the <strong>Empty</strong> placeholder model. Select a real model
          provider and model below to generate data.
        </Alert>
      )}

      {/* Dataset Purpose */}
      <TextField
        label="Dataset Purpose"
        placeholder="Describe what this dataset is for and what kind of data it contains..."
        multiline
        rows={3}
        value={datasetPurpose}
        onChange={(e) => setDatasetPurpose(e.target.value)}
        fullWidth
        required
        helperText="Help the AI understand the context and purpose of your data"
      />

      {/* Column Descriptions */}
      <Box>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Column Descriptions
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Describe what each column contains to guide realistic data generation
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {columnDescriptions.map((col) => (
            <TextField
              key={col.columnName}
              label={col.columnName}
              placeholder={`Describe what "${col.columnName}" contains...`}
              value={col.description}
              onChange={(e) => handleColumnDescriptionChange(col.columnName, e.target.value)}
              fullWidth
              size="small"
              required
            />
          ))}
        </Box>
      </Box>

      {/* Model Selection — only shown when the stored prompt uses a placeholder */}
      {promptStatus?.is_placeholder && (
        <Box sx={{ display: "flex", gap: 2 }}>
          <FormControl fullWidth size="small">
            <InputLabel>Model Provider</InputLabel>
            <Select value={modelProvider || ""} label="Model Provider" onChange={(e) => setModelProvider(e.target.value as ModelProvider)}>
              {enabledProviders.map((provider) => (
                <MenuItem key={provider.provider} value={provider.provider}>
                  {provider.provider.charAt(0).toUpperCase() + provider.provider.slice(1)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Autocomplete
            fullWidth
            size="small"
            options={availableModels}
            value={modelName}
            onChange={(_, newValue) => setModelName(newValue)}
            loading={isLoadingModels}
            disabled={!modelProvider || isLoadingModels}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Model"
                placeholder="Select a model"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {isLoadingModels ? <CircularProgress color="inherit" size={20} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
          />
        </Box>
      )}

      {/* Number of Rows */}
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Number of Rows to Generate: {numRows}
        </Typography>
        <Slider
          value={numRows}
          onChange={(_, value) => setNumRows(value as number)}
          min={1}
          max={25}
          marks={[
            { value: 1, label: "1" },
            { value: 10, label: "10" },
            { value: 25, label: "25" },
          ]}
          valueLabelDisplay="auto"
        />
      </Box>

      {/* Edit Existing Data Toggle */}
      <Box>
        <FormControlLabel
          control={<Switch checked={editExisting} onChange={(e) => setEditExisting(e.target.checked)} />}
          label="Edit existing data"
        />
        <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
          {editExisting
            ? "Existing dataset rows will be loaded into the canvas for editing and synthetic generation will update them"
            : "Only new rows will be generated without modifying existing data"}
        </Typography>
      </Box>

      {/* Actions */}
      <Box sx={{ display: "flex", justifyContent: "flex-end", gap: 2, pt: 2 }}>
        <Button onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!canSubmit || isLoading}
          startIcon={isLoading ? <CircularProgress size={16} /> : null}
        >
          {isLoading ? "Generating..." : "Start Generating"}
        </Button>
      </Box>
    </Box>
  );
};
