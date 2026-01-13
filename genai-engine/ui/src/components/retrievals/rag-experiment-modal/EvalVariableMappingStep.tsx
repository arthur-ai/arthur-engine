import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import TableChartOutlinedIcon from "@mui/icons-material/TableChartOutlined";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import React, { useState } from "react";

import type { EvaluatorSelection, VariableSourceType, FormValues, EvalVariableMappings } from "./types";
import { useRagExperimentForm } from "./useRagExperimentForm";

// Infer form type from the hook
type FormInstance = ReturnType<typeof useRagExperimentForm>["form"];

// Predefined JSON path options for RAG output extraction
interface JsonPathOption {
  label: string;
  value: string;
  description: string;
}

const JSON_PATH_OPTIONS: JsonPathOption[] = [
  { label: "Full RAG Output", value: "", description: "Pass entire search response as JSON" },
  { label: "All Search Results", value: "response.objects", description: "Array of all matched documents" },
  { label: "First Result", value: "response.objects.0", description: "Top matching document only" },
  { label: "First Result Content", value: "response.objects.0.properties", description: "Properties/content of top result" },
  { label: "First Result Score", value: "response.objects.0.metadata.score", description: "Relevance score of top result" },
  { label: "Custom Path...", value: "__custom__", description: "Enter a custom JSON path" },
];

interface EvalVariableMappingStepProps {
  form: FormInstance;
  evaluator: EvaluatorSelection;
  evalIndex: number;
  totalEvaluators: number;
  variables: string[];
  datasetColumns: string[];
  loadingEvalDetails: boolean;
  loadingInstructions: boolean;
  onViewInstructions: () => void;
}

export const EvalVariableMappingStep: React.FC<EvalVariableMappingStepProps> = ({
  form,
  evaluator,
  evalIndex,
  totalEvaluators,
  variables,
  datasetColumns,
  loadingEvalDetails,
  loadingInstructions,
  onViewInstructions,
}) => {
  const [customPathMode, setCustomPathMode] = useState<Record<string, boolean>>({});

  return (
    <Box className="flex flex-col gap-4 mt-2">
      <Box className="flex items-center justify-between mb-2">
        <Typography variant="h6">
          {evaluator.name} v{evaluator.version}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Evaluator {evalIndex + 1} of {totalEvaluators}
        </Typography>
      </Box>

      <Button variant="text" size="small" onClick={onViewInstructions} disabled={loadingInstructions}>
        {loadingInstructions ? <CircularProgress size={16} /> : "View Instructions"}
      </Button>

      {loadingEvalDetails ? (
        <Box className="flex justify-center py-4">
          <CircularProgress />
        </Box>
      ) : variables.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          This evaluator has no variables to configure.
        </Typography>
      ) : (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            For RAG evaluators, variables typically map to the experiment output (the RAG response). Use "Dataset Column" only for ground-truth or
            reference data.
          </Typography>
          <form.Field name="evalVariableMappings">
            {(field) => {
              const fieldValue = field.state.value as EvalVariableMappings[];
              const existingMappings = fieldValue.find((m) => m.evalName === evaluator.name && m.evalVersion === evaluator.version);

              const handleVariableChange = (variableName: string, sourceType: VariableSourceType, value: string) => {
                const currentMappings = [...fieldValue];
                const existingIndex = currentMappings.findIndex((m) => m.evalName === evaluator.name && m.evalVersion === evaluator.version);

                const newMapping: EvalVariableMappings =
                  existingIndex >= 0
                    ? { ...currentMappings[existingIndex] }
                    : { evalName: evaluator.name, evalVersion: evaluator.version, mappings: {} };

                newMapping.mappings = {
                  ...newMapping.mappings,
                  [variableName]: {
                    sourceType,
                    ...(sourceType === "dataset_column" ? { datasetColumn: value } : { jsonPath: value }),
                  },
                };

                const newMappings =
                  existingIndex >= 0 ? currentMappings.map((m, i) => (i === existingIndex ? newMapping : m)) : [...currentMappings, newMapping];

                field.handleChange(newMappings as FormValues["evalVariableMappings"]);
              };

              return (
                <>
                  {variables.map((variableName) => {
                    const currentMapping = existingMappings?.mappings[variableName];
                    const sourceType = currentMapping?.sourceType || "experiment_output";

                    return (
                      <Card key={variableName} variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2" className="font-semibold mb-2">
                            {variableName}
                          </Typography>

                          <Box className="flex flex-col gap-3">
                            <ToggleButtonGroup
                              value={sourceType}
                              exclusive
                              onChange={(_, value) => {
                                if (value) {
                                  handleVariableChange(variableName, value, "");
                                  // Reset custom path mode when switching source types
                                  if (value === "dataset_column") {
                                    setCustomPathMode((prev) => ({ ...prev, [variableName]: false }));
                                  }
                                }
                              }}
                              size="small"
                              sx={{ alignSelf: "flex-start" }}
                            >
                              <ToggleButton value="dataset_column" sx={{ px: 2, py: 1 }}>
                                <Box className="flex flex-col items-center text-center">
                                  <TableChartOutlinedIcon fontSize="small" />
                                  <Typography variant="caption" fontWeight="bold" sx={{ textTransform: "none" }}>
                                    Ground Truth
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem", textTransform: "none" }}>
                                    From dataset
                                  </Typography>
                                </Box>
                              </ToggleButton>
                              <ToggleButton value="experiment_output" sx={{ px: 2, py: 1 }}>
                                <Box className="flex flex-col items-center text-center">
                                  <AutoAwesomeOutlinedIcon fontSize="small" />
                                  <Typography variant="caption" fontWeight="bold" sx={{ textTransform: "none" }}>
                                    RAG Response
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary" sx={{ fontSize: "0.65rem", textTransform: "none" }}>
                                    Search results
                                  </Typography>
                                </Box>
                              </ToggleButton>
                            </ToggleButtonGroup>

                            {sourceType === "dataset_column" ? (
                              <FormControl sx={{ flex: 1 }}>
                                <InputLabel>Column</InputLabel>
                                <Select
                                  value={currentMapping?.datasetColumn || ""}
                                  onChange={(e) => handleVariableChange(variableName, "dataset_column", e.target.value)}
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
                            ) : customPathMode[variableName] ? (
                              <TextField
                                label="Custom JSON Path"
                                value={currentMapping?.jsonPath || ""}
                                onChange={(e) => handleVariableChange(variableName, "experiment_output", e.target.value)}
                                placeholder="e.g. response.objects.0.properties.content"
                                helperText="Use dot notation for nested fields (e.g. response.objects.0.properties)"
                                size="small"
                                fullWidth
                                InputProps={{
                                  endAdornment: (
                                    <Button
                                      size="small"
                                      onClick={() => setCustomPathMode((prev) => ({ ...prev, [variableName]: false }))}
                                      sx={{ minWidth: "auto", fontSize: "0.75rem" }}
                                    >
                                      Presets
                                    </Button>
                                  ),
                                }}
                              />
                            ) : (
                              <Autocomplete
                                options={JSON_PATH_OPTIONS}
                                getOptionLabel={(option) => (typeof option === "string" ? option : option.label)}
                                value={JSON_PATH_OPTIONS.find((opt) => opt.value === (currentMapping?.jsonPath || "")) || JSON_PATH_OPTIONS[0]}
                                onChange={(_, newValue) => {
                                  if (newValue && typeof newValue !== "string") {
                                    if (newValue.value === "__custom__") {
                                      setCustomPathMode((prev) => ({ ...prev, [variableName]: true }));
                                      handleVariableChange(variableName, "experiment_output", "");
                                    } else {
                                      handleVariableChange(variableName, "experiment_output", newValue.value);
                                    }
                                  }
                                }}
                                isOptionEqualToValue={(option, value) => option.value === value.value}
                                renderOption={(props, option) => {
                                  const { key, ...otherProps } = props;
                                  return (
                                    <li key={key} {...otherProps}>
                                      <Box className="flex flex-col py-1">
                                        <Typography variant="body2">{option.label}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                          {option.description}
                                        </Typography>
                                      </Box>
                                    </li>
                                  );
                                }}
                                renderInput={(params) => <TextField {...params} label="Extract from RAG output" size="small" />}
                                fullWidth
                                disableClearable
                              />
                            )}
                          </Box>
                        </CardContent>
                      </Card>
                    );
                  })}
                </>
              );
            }}
          </form.Field>
        </>
      )}
    </Box>
  );
};
