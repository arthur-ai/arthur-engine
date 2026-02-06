import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { TextField, Box, Autocomplete, Chip, FormControl, InputLabel, Select, MenuItem, Typography, Tooltip, Button } from "@mui/material";
import React from "react";
import { z } from "zod";

import type { RagConfigSelection, FormValues, EvaluatorSelection, DatasetRowFilter } from "./types";
import { useRagExperimentForm } from "./useRagExperimentForm";

import type {
  DatasetResponse,
  DatasetVersionMetadataResponse,
  LLMGetAllMetadataResponse,
  LLMVersionResponse,
  RagSearchSettingConfigurationResponse,
  RagSearchSettingConfigurationVersionResponse,
} from "@/lib/api-client/api-client";

// Infer form type from the hook
type FormInstance = ReturnType<typeof useRagExperimentForm>["form"];

interface ExperimentInfoStepProps {
  form: FormInstance;
  /** Whether we're in saved configs mode (no panels provided) */
  isSavedConfigsMode: boolean;
  /** Available configs derived from panels (panel mode only) */
  availableRagConfigs: RagConfigSelection[];
  /** Saved RAG configs from API (saved configs mode only) */
  savedRagConfigs?: RagSearchSettingConfigurationResponse[];
  savedConfigVersions?: Record<string, RagSearchSettingConfigurationVersionResponse[]>;
  loadingSavedRagConfigs?: boolean;
  loadingSavedConfigVersions?: boolean;
  selectedSavedConfigId?: string;
  setSelectedSavedConfigId?: (id: string) => void;
  selectedSavedConfigVersion?: number | "";
  setSelectedSavedConfigVersion?: (version: number | "") => void;
  onLoadSavedConfigVersions?: (configId: string) => void;
  onAddSavedRagConfig?: () => void;
  onRemoveRagConfig?: (index: number) => void;
  datasets: DatasetResponse[];
  datasetVersions: DatasetVersionMetadataResponse[];
  datasetColumns: string[];
  evaluators: LLMGetAllMetadataResponse[];
  evaluatorVersions: Record<string, LLMVersionResponse[]>;
  loadingDatasets: boolean;
  loadingDatasetVersions: boolean;
  loadingEvaluators: boolean;
  currentEvaluatorName: string;
  setCurrentEvaluatorName: (name: string) => void;
  currentEvaluatorVersion: number | "";
  setCurrentEvaluatorVersion: (version: number | "") => void;
  onDatasetSelect: (datasetId: string) => void;
  onEvaluatorNameSelect: (name: string) => void;
  onAddEvaluator: () => void;
  onRemoveEvaluator: (index: number) => void;
  onToggleRagConfig: (config: RagConfigSelection) => void;
}

export const ExperimentInfoStep: React.FC<ExperimentInfoStepProps> = ({
  form,
  isSavedConfigsMode,
  availableRagConfigs,
  savedRagConfigs = [],
  savedConfigVersions = {},
  loadingSavedRagConfigs = false,
  loadingSavedConfigVersions = false,
  selectedSavedConfigId = "",
  setSelectedSavedConfigId,
  selectedSavedConfigVersion = "",
  setSelectedSavedConfigVersion,
  onLoadSavedConfigVersions,
  onAddSavedRagConfig,
  onRemoveRagConfig,
  datasets,
  datasetVersions,
  datasetColumns,
  evaluators,
  evaluatorVersions,
  loadingDatasets,
  loadingDatasetVersions,
  loadingEvaluators,
  currentEvaluatorName,
  setCurrentEvaluatorName,
  currentEvaluatorVersion,
  setCurrentEvaluatorVersion,
  onDatasetSelect,
  onEvaluatorNameSelect,
  onAddEvaluator,
  onRemoveEvaluator,
  onToggleRagConfig,
}) => {
  return (
    <Box className="flex flex-col gap-4 mt-2">
      {/* Experiment Name Field */}
      <form.Field
        name="name"
        validators={{
          onChange: ({ value }: { value: string }) => {
            const result = z.string().min(1, "Experiment name is required").safeParse(value);
            return result.success ? undefined : result.error.issues[0].message;
          },
        }}
      >
        {(field) => (
          <TextField
            label="Experiment Name"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            error={field.state.meta.errors.length > 0}
            helperText={field.state.meta.errors[0]}
            fullWidth
            required
            placeholder="e.g., RAG Search Quality Test"
            autoFocus
          />
        )}
      </form.Field>

      {/* Description Field */}
      <form.Field name="description">
        {(field) => (
          <TextField
            label="Description"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            onBlur={field.handleBlur}
            fullWidth
            multiline
            rows={2}
            placeholder="Describe the purpose of this experiment"
          />
        )}
      </form.Field>

      {/* RAG Configuration Selection */}
      <form.Field name="ragConfigs">
        {(field) => (
          <Box className="border border-gray-300 rounded p-4">
            <Box className="flex items-center gap-2 mb-2">
              <Typography variant="subtitle1" className="font-semibold">
                RAG Configurations *
              </Typography>
              <Tooltip
                title={
                  isSavedConfigsMode
                    ? "Select saved RAG configurations to test in this experiment."
                    : "Select which RAG configurations from your panels to include in the experiment. Each configuration will be tested against all rows in your dataset."
                }
                arrow
                placement="right"
              >
                <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", cursor: "help" }} />
              </Tooltip>
            </Box>

            {isSavedConfigsMode ? (
              /* Saved configs mode - show dropdown to select saved configs */
              <>
                <Box className="flex gap-2 mb-3 mt-2">
                  <Autocomplete
                    options={savedRagConfigs}
                    getOptionLabel={(option) => option.name}
                    value={savedRagConfigs.find((c) => c.id === selectedSavedConfigId) || null}
                    onChange={(_, value) => {
                      setSelectedSavedConfigId?.(value?.id || "");
                      setSelectedSavedConfigVersion?.("");
                      if (value && onLoadSavedConfigVersions) {
                        onLoadSavedConfigVersions(value.id);
                      }
                    }}
                    loading={loadingSavedRagConfigs}
                    renderInput={(params) => <TextField {...params} label="Select Configuration" placeholder="Search configurations..." />}
                    className="flex-1"
                  />

                  <FormControl sx={{ minWidth: 100 }}>
                    <InputLabel>Version</InputLabel>
                    <Select
                      value={selectedSavedConfigVersion}
                      onChange={(e) => setSelectedSavedConfigVersion?.(e.target.value as number)}
                      label="Version"
                      disabled={!selectedSavedConfigId || loadingSavedConfigVersions}
                    >
                      {(savedConfigVersions[selectedSavedConfigId] || []).map((v) => (
                        <MenuItem key={v.version_number} value={v.version_number}>
                          v{v.version_number}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <Button
                    variant="outlined"
                    onClick={onAddSavedRagConfig}
                    disabled={!selectedSavedConfigId || !selectedSavedConfigVersion}
                    startIcon={<AddIcon />}
                  >
                    Add
                  </Button>
                </Box>

                {(field.state.value as RagConfigSelection[]).length > 0 && (
                  <Box className="flex flex-wrap gap-2">
                    {(field.state.value as RagConfigSelection[]).map((config, index) => (
                      <Chip
                        key={config.panelId}
                        label={config.displayName}
                        onDelete={() => onRemoveRagConfig?.(index)}
                        color="primary"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                )}
              </>
            ) : (
              /* Panel mode - show toggle chips for available configs */
              <>
                {availableRagConfigs.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No configured RAG panels available. Please configure at least one panel with a provider and collection.
                  </Typography>
                ) : (
                  <Box className="flex flex-wrap gap-2 mt-2">
                    {availableRagConfigs.map((config) => {
                      const isSelected = (field.state.value as RagConfigSelection[]).some((c) => c.panelId === config.panelId);
                      return (
                        <Chip
                          key={config.panelId}
                          label={config.displayName}
                          onClick={() => onToggleRagConfig(config)}
                          color={isSelected ? "primary" : "default"}
                          variant={isSelected ? "filled" : "outlined"}
                          sx={{ cursor: "pointer" }}
                        />
                      );
                    })}
                  </Box>
                )}
              </>
            )}
            {field.state.meta.errors.length > 0 && (
              <Typography variant="caption" color="error" className="mt-1">
                {field.state.meta.errors[0]}
              </Typography>
            )}
          </Box>
        )}
      </form.Field>

      {/* Dataset Selection */}
      <Box className="border border-gray-300 rounded p-4">
        <Box className="flex items-center gap-2 mb-2">
          <Typography variant="subtitle1" className="font-semibold">
            Dataset *
          </Typography>
          <Tooltip title="Select a dataset containing test queries and expected results." arrow placement="right">
            <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", cursor: "help" }} />
          </Tooltip>
        </Box>

        <Box className="flex gap-2 mt-2">
          <form.Field name="datasetId">
            {(field) => (
              <Autocomplete
                options={datasets}
                getOptionLabel={(option) => option.name}
                value={datasets.find((d) => d.id === field.state.value) || null}
                onChange={(_, value) => {
                  if (value) {
                    field.handleChange(value.id);
                    form.setFieldValue("datasetName", value.name);
                    form.setFieldValue("datasetVersion", "");
                    onDatasetSelect(value.id);
                  } else {
                    field.handleChange("");
                    form.setFieldValue("datasetName", "");
                    form.setFieldValue("datasetVersion", "");
                  }
                }}
                loading={loadingDatasets}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Dataset"
                    placeholder="Search datasets..."
                    error={field.state.meta.errors.length > 0}
                    helperText={field.state.meta.errors[0]}
                  />
                )}
                className="flex-1"
              />
            )}
          </form.Field>

          <form.Field name="datasetVersion">
            {(field) => {
              const datasetId = form.getFieldValue("datasetId");
              return (
                <FormControl sx={{ minWidth: 120 }} error={field.state.meta.errors.length > 0}>
                  <InputLabel>Version</InputLabel>
                  <Select
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value as number)}
                    label="Version"
                    disabled={!datasetId || loadingDatasetVersions}
                  >
                    {datasetVersions.map((v) => (
                      <MenuItem key={v.version_number} value={v.version_number}>
                        v{v.version_number}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              );
            }}
          </form.Field>
        </Box>
      </Box>

      {/* Query Column Selection */}
      {datasetColumns.length > 0 && (
        <form.Field name="queryColumn">
          {(field) => (
            <Box className="border border-gray-300 rounded p-4">
              <Box className="flex items-center gap-2 mb-2">
                <Typography variant="subtitle1" className="font-semibold">
                  Query Column *
                </Typography>
                <Tooltip
                  title="Select the dataset column containing the search queries. This column will be used as input for all RAG configurations."
                  arrow
                  placement="right"
                >
                  <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", cursor: "help" }} />
                </Tooltip>
              </Box>

              <FormControl fullWidth error={field.state.meta.errors.length > 0}>
                <InputLabel>Select Query Column</InputLabel>
                <Select value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} label="Select Query Column">
                  {datasetColumns.map((col) => (
                    <MenuItem key={col} value={col}>
                      {col}
                    </MenuItem>
                  ))}
                </Select>
                {field.state.meta.errors.length > 0 && (
                  <Typography variant="caption" color="error" className="mt-1">
                    {field.state.meta.errors[0]}
                  </Typography>
                )}
              </FormControl>
            </Box>
          )}
        </form.Field>
      )}

      {/* Dataset Row Filter */}
      {datasetColumns.length > 0 && (
        <form.Field name="datasetRowFilter">
          {(field) => (
            <Box className="border border-gray-300 rounded p-4">
              <Box className="flex items-center gap-2 mb-2">
                <Typography variant="subtitle1" className="font-semibold">
                  Dataset Row Filter (Optional)
                </Typography>
                <Tooltip
                  title="Optionally filter which dataset rows to include in the experiment. Only rows matching ALL specified filters will be used."
                  arrow
                  placement="right"
                >
                  <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", cursor: "help" }} />
                </Tooltip>
              </Box>

              {(field.state.value as DatasetRowFilter[]).map((filter, index) => (
                <Box key={index} className="flex gap-2 mb-2 items-center">
                  <FormControl sx={{ minWidth: 150 }}>
                    <InputLabel>Column</InputLabel>
                    <Select
                      value={filter.column_name}
                      onChange={(e) => {
                        const currentValue = field.state.value as DatasetRowFilter[];
                        const newFilters = [...currentValue];
                        newFilters[index] = { ...filter, column_name: e.target.value };
                        field.handleChange(newFilters as FormValues["datasetRowFilter"]);
                      }}
                      label="Column"
                      size="small"
                    >
                      {datasetColumns.map((col) => (
                        <MenuItem key={col} value={col}>
                          {col}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <TextField
                    label="Value"
                    value={filter.column_value}
                    onChange={(e) => {
                      const currentValue = field.state.value as DatasetRowFilter[];
                      const newFilters = [...currentValue];
                      newFilters[index] = { ...filter, column_value: e.target.value };
                      field.handleChange(newFilters as FormValues["datasetRowFilter"]);
                    }}
                    size="small"
                    sx={{ flex: 1 }}
                  />

                  <Button
                    variant="outlined"
                    color="error"
                    size="small"
                    onClick={() => {
                      const currentValue = field.state.value as DatasetRowFilter[];
                      field.handleChange(currentValue.filter((_, i) => i !== index) as FormValues["datasetRowFilter"]);
                    }}
                  >
                    <CloseIcon fontSize="small" />
                  </Button>
                </Box>
              ))}

              <Button
                variant="outlined"
                size="small"
                startIcon={<AddIcon />}
                onClick={() => {
                  const currentValue = field.state.value as DatasetRowFilter[];
                  field.handleChange([...currentValue, { column_name: "", column_value: "" }] as FormValues["datasetRowFilter"]);
                }}
              >
                Add Filter
              </Button>
            </Box>
          )}
        </form.Field>
      )}

      {/* Evaluator Selection */}
      <form.Field name="evaluators">
        {(field) => (
          <Box className="border border-gray-300 rounded p-4">
            <Box className="flex items-center gap-2 mb-2">
              <Typography variant="subtitle1" className="font-semibold">
                Evaluators *
              </Typography>
              <Tooltip
                title="Select evaluators to assess the quality of RAG search results. Each evaluator will be run on every test case."
                arrow
                placement="right"
              >
                <InfoOutlinedIcon sx={{ fontSize: 18, color: "text.secondary", cursor: "help" }} />
              </Tooltip>
            </Box>

            <Box className="flex gap-2 mb-3 mt-4">
              <Autocomplete
                options={evaluators}
                getOptionLabel={(option) => option.name}
                value={evaluators.find((e) => e.name === currentEvaluatorName) || null}
                onChange={(_, value) => {
                  setCurrentEvaluatorName(value?.name || "");
                  setCurrentEvaluatorVersion("");
                  if (value) {
                    onEvaluatorNameSelect(value.name);
                  }
                }}
                loading={loadingEvaluators}
                renderInput={(params) => <TextField {...params} label="Select Evaluator" placeholder="Search evaluators..." />}
                className="flex-1"
              />

              <FormControl sx={{ minWidth: 100 }}>
                <InputLabel>Version</InputLabel>
                <Select
                  value={currentEvaluatorVersion}
                  onChange={(e) => setCurrentEvaluatorVersion(e.target.value as number)}
                  label="Version"
                  disabled={!currentEvaluatorName}
                >
                  {(evaluatorVersions[currentEvaluatorName] || []).map((v) => (
                    <MenuItem key={v.version} value={v.version}>
                      v{v.version}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                variant="outlined"
                onClick={onAddEvaluator}
                disabled={!currentEvaluatorName || !currentEvaluatorVersion}
                startIcon={<AddIcon />}
              >
                Add
              </Button>
            </Box>

            {(field.state.value as EvaluatorSelection[]).length > 0 && (
              <Box className="flex flex-wrap gap-2">
                {(field.state.value as EvaluatorSelection[]).map((evaluator, index) => (
                  <Chip
                    key={`${evaluator.name}-${evaluator.version}`}
                    label={`${evaluator.name} v${evaluator.version}`}
                    onDelete={() => onRemoveEvaluator(index)}
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
            )}

            {field.state.meta.errors.length > 0 && (
              <Typography variant="caption" color="error" className="mt-1">
                {field.state.meta.errors[0]}
              </Typography>
            )}
          </Box>
        )}
      </form.Field>
    </Box>
  );
};
