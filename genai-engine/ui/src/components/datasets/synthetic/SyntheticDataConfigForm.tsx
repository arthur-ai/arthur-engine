import {
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  TextField,
  Typography,
  Autocomplete,
  Alert,
} from "@mui/material";
import React, { useCallback, useEffect, useState } from "react";

import type { GenerationConfig } from "./types";

import { useApi } from "@/hooks/useApi";
import type {
  DatasetVersionRowResponse,
  ModelProvider,
  ModelProviderResponse,
} from "@/lib/api-client/api-client";

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
  const [columnDescriptions, setColumnDescriptions] = useState<ColumnDescription[]>(
    columns.map((col) => ({ columnName: col, description: "" }))
  );
  const [numRows, setNumRows] = useState(10);
  const [modelProvider, setModelProvider] = useState<ModelProvider | null>(null);
  const [modelName, setModelName] = useState<string | null>(null);
  const [temperature, setTemperature] = useState(0.7);

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
        const enabledProviders = (response.data.providers || []).filter(
          (p) => p.enabled
        );
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
        const response =
          await api.api.getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet(
            modelProvider
          );
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

  const handleColumnDescriptionChange = useCallback(
    (columnName: string, description: string) => {
      setColumnDescriptions((prev) =>
        prev.map((col) =>
          col.columnName === columnName ? { ...col, description } : col
        )
      );
    },
    []
  );

  const handleSubmit = useCallback(() => {
    if (!modelProvider || !modelName) return;

    onSubmit({
      datasetPurpose,
      columnDescriptions,
      numRows,
      modelProvider,
      modelName,
      temperature,
    });
  }, [
    datasetPurpose,
    columnDescriptions,
    numRows,
    modelProvider,
    modelName,
    temperature,
    onSubmit,
  ]);

  const enabledProviders = providers.filter((p) => p.enabled);
  const canSubmit =
    datasetPurpose.trim() &&
    modelProvider &&
    modelName &&
    columnDescriptions.every((col) => col.description.trim());

  if (isLoadingProviders) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (enabledProviders.length === 0) {
    return (
      <Box sx={{ py: 2 }}>
        <Alert severity="warning">
          No model providers are configured. Please configure at least one model
          provider in Settings to use synthetic data generation.
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
              onChange={(e) =>
                handleColumnDescriptionChange(col.columnName, e.target.value)
              }
              fullWidth
              size="small"
              required
            />
          ))}
        </Box>
      </Box>

      {/* Model Selection */}
      <Box sx={{ display: "flex", gap: 2 }}>
        <FormControl fullWidth size="small">
          <InputLabel>Model Provider</InputLabel>
          <Select
            value={modelProvider || ""}
            label="Model Provider"
            onChange={(e) => setModelProvider(e.target.value as ModelProvider)}
          >
            {enabledProviders.map((provider) => (
              <MenuItem key={provider.provider} value={provider.provider}>
                {provider.provider.charAt(0).toUpperCase() +
                  provider.provider.slice(1)}
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
                    {isLoadingModels ? (
                      <CircularProgress color="inherit" size={20} />
                    ) : null}
                    {params.InputProps.endAdornment}
                  </>
                ),
              }}
            />
          )}
        />
      </Box>

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

      {/* Temperature */}
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          Temperature: {temperature.toFixed(1)}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Higher values produce more varied/creative data
        </Typography>
        <Slider
          value={temperature}
          onChange={(_, value) => setTemperature(value as number)}
          min={0}
          max={1}
          step={0.1}
          marks={[
            { value: 0, label: "0" },
            { value: 0.5, label: "0.5" },
            { value: 1, label: "1" },
          ]}
          valueLabelDisplay="auto"
        />
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
