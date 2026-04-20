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
import React, { useCallback, useState } from "react";

import type { GenerationConfig } from "./types";

import { useApiQuery } from "@/hooks/useApiQuery";
import type { DatasetVersionRowResponse, ModelProvider } from "@/lib/api-client/api-client";

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
  // Form state
  const [datasetPurpose, setDatasetPurpose] = useState("");
  const [columnDescriptions, setColumnDescriptions] = useState<ColumnDescription[]>(columns.map((col) => ({ columnName: col, description: "" })));
  const [numRows, setNumRows] = useState(10);
  const [editExisting, setEditExisting] = useState(false);

  // User's explicit model selection (only used in placeholder mode). When null,
  // we fall back to the first enabled provider / no model until the user picks.
  const [selectedProvider, setSelectedProvider] = useState<ModelProvider | null>(null);
  const [selectedModelName, setSelectedModelName] = useState<string | null>(null);

  const { data: promptStatus, isLoading: isLoadingPromptStatus } =
    useApiQuery<"getSyntheticDataPromptStatusApiV2DatasetsSyntheticDataPromptStatusGet">({
      method: "getSyntheticDataPromptStatusApiV2DatasetsSyntheticDataPromptStatusGet",
      args: [] as const,
      queryOptions: { staleTime: 60000, refetchOnWindowFocus: false },
    });

  // When the stored prompt already has a real model, the selection UI is hidden
  // and the form submits the stored values directly.
  const usesStoredModel = promptStatus?.is_placeholder === false;

  const { data: providersResponse, isLoading: isLoadingProviders } = useApiQuery<"getModelProvidersApiV1ModelProvidersGet">({
    method: "getModelProvidersApiV1ModelProvidersGet",
    args: [] as const,
    enabled: promptStatus !== undefined && promptStatus.is_placeholder,
    queryOptions: { staleTime: 60000, refetchOnWindowFocus: false },
  });

  const enabledProviders = (providersResponse?.providers ?? []).filter((p) => p.enabled);

  // Derive the provider to use: user's choice > auto-selected first enabled > none.
  const activeProvider: ModelProvider | null = selectedProvider ?? enabledProviders[0]?.provider ?? null;

  const { data: availableModelsResponse, isLoading: isLoadingModels } =
    useApiQuery<"getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet">({
      method: "getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet",
      // TS needs the tuple shape even when the query is disabled.
      args: [activeProvider as ModelProvider] as const,
      enabled: !!activeProvider && promptStatus?.is_placeholder === true,
      queryOptions: { staleTime: 60000, refetchOnWindowFocus: false },
    });

  const availableModels = availableModelsResponse?.available_models ?? [];

  // Coerce stale model selections to null when the list changes — avoids the
  // setState-inside-useEffect pattern the old code used.
  const activeModelName: string | null = selectedModelName && availableModels.includes(selectedModelName) ? selectedModelName : null;

  const handleColumnDescriptionChange = useCallback((columnName: string, description: string) => {
    setColumnDescriptions((prev) => prev.map((col) => (col.columnName === columnName ? { ...col, description } : col)));
  }, []);

  // Effective values used for submission: stored prompt values when non-placeholder,
  // otherwise the in-form user selection (falling back to auto-select for provider).
  const effectiveModelProvider: ModelProvider | null = usesStoredModel ? (promptStatus.model_provider as ModelProvider) : activeProvider;
  const effectiveModelName: string | null = usesStoredModel ? promptStatus.model_name : activeModelName;

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

  const canSubmit =
    datasetPurpose.trim() && effectiveModelProvider && effectiveModelName && columnDescriptions.every((col) => col.description.trim());

  // Wait for prompt status and (when relevant) providers before rendering the form.
  const waitingForInitialLoad = isLoadingPromptStatus || (promptStatus?.is_placeholder && isLoadingProviders);
  if (waitingForInitialLoad) {
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
            <Select
              value={activeProvider ?? ""}
              label="Model Provider"
              onChange={(e) => {
                setSelectedProvider(e.target.value as ModelProvider);
                setSelectedModelName(null);
              }}
            >
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
            value={activeModelName}
            onChange={(_, newValue) => setSelectedModelName(newValue)}
            loading={isLoadingModels}
            disabled={!activeProvider || isLoadingModels}
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
