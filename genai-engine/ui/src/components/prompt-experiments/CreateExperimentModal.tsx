import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  CircularProgress,
  Autocomplete,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  IconButton,
  Stepper,
  Step,
  StepLabel,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import type {
  LLMGetAllMetadataResponse,
  AgenticPromptVersionResponse,
  DatasetResponse,
  DatasetVersionMetadataResponse,
  LLMEvalsVersionListResponse,
  LLMVersionResponse,
  AgenticPrompt,
  LLMEval,
} from "@/lib/api-client/api-client";

interface CreateExperimentModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: ExperimentFormData) => Promise<void>;
}

export interface PromptVersionSelection {
  promptName: string;
  version: number;
}

export interface EvaluatorSelection {
  name: string;
  version: number;
}

export type VariableSourceType = "dataset_column" | "experiment_output";

export interface VariableMapping {
  variableName: string;
  sourceType: VariableSourceType;
  datasetColumn?: string;  // For dataset_column source
  jsonPath?: string;       // For experiment_output source
}

export interface PromptVariableMappings {
  [variableName: string]: string; // variable name -> dataset column name
}

export interface EvalVariableMappings {
  evalName: string;
  evalVersion: number;
  mappings: {
    [variableName: string]: {
      sourceType: VariableSourceType;
      datasetColumn?: string;
      jsonPath?: string;
    };
  };
}

export interface ExperimentFormData {
  name: string;
  description: string;
  promptVersions: PromptVersionSelection[];
  datasetId: string;
  datasetVersion: number | "";
  evaluators: EvaluatorSelection[];
  promptVariableMappings?: PromptVariableMappings;
  evalVariableMappings?: EvalVariableMappings[];
}

export const CreateExperimentModal: React.FC<CreateExperimentModalProps> = ({
  open,
  onClose,
  onSubmit,
}) => {
  const { id: taskId } = useParams<{ id: string }>();
  const api = useApi();

  // Step management
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [currentEvalIndex, setCurrentEvalIndex] = useState(0); // Track which eval is being configured in step 2

  // Form state
  const [formData, setFormData] = useState<ExperimentFormData>({
    name: "",
    description: "",
    promptVersions: [],
    datasetId: "",
    datasetVersion: "",
    evaluators: [],
    promptVariableMappings: {},
    evalVariableMappings: [],
  });

  // Prompts state
  const [prompts, setPrompts] = useState<LLMGetAllMetadataResponse[]>([]);
  const [selectedPromptName, setSelectedPromptName] = useState<string>("");
  const [promptVersions, setPromptVersions] = useState<AgenticPromptVersionResponse[]>([]);
  const [visibleOlderVersions, setVisibleOlderVersions] = useState<number[]>([]);
  const [loadingPrompts, setLoadingPrompts] = useState(false);
  const [loadingPromptVersions, setLoadingPromptVersions] = useState(false);

  // Datasets state
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [datasetVersions, setDatasetVersions] = useState<DatasetVersionMetadataResponse[]>([]);
  const [datasetColumns, setDatasetColumns] = useState<string[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(false);
  const [loadingDatasetVersions, setLoadingDatasetVersions] = useState(false);

  // Prompt and eval variable details
  const [promptVariables, setPromptVariables] = useState<string[]>([]);
  const [loadingPromptDetails, setLoadingPromptDetails] = useState(false);
  const [evalVariables, setEvalVariables] = useState<Record<string, { name: string; version: number; variables: string[] }>>({});
  const [loadingEvalDetails, setLoadingEvalDetails] = useState(false);

  // Evaluators state
  const [evaluators, setEvaluators] = useState<LLMGetAllMetadataResponse[]>([]);
  const [evaluatorVersions, setEvaluatorVersions] = useState<Record<string, LLMVersionResponse[]>>({});
  const [loadingEvaluators, setLoadingEvaluators] = useState(false);
  const [currentEvaluatorName, setCurrentEvaluatorName] = useState<string>("");
  const [currentEvaluatorVersion, setCurrentEvaluatorVersion] = useState<number | "">("");

  const [errors, setErrors] = useState<Partial<Record<keyof ExperimentFormData | "general", string>>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load prompts on mount
  useEffect(() => {
    if (open && taskId && api) {
      loadPrompts();
      loadDatasets();
      loadEvaluators();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, taskId, api]);

  // Load prompt versions when a prompt is selected
  useEffect(() => {
    if (selectedPromptName && taskId && api) {
      loadPromptVersions(selectedPromptName);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPromptName, taskId, api]);

  const loadPrompts = async () => {
    if (!taskId || !api) return;
    try {
      setLoadingPrompts(true);
      const response = await api.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
        taskId,
        page_size: 100,
      });
      setPrompts(response.data.llm_metadata);
    } catch (error) {
      console.error("Failed to load prompts:", error);
    } finally {
      setLoadingPrompts(false);
    }
  };

  const loadPromptVersions = async (promptName: string) => {
    if (!taskId || !api) return;
    try {
      setLoadingPromptVersions(true);
      const response = await api.api.getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet({
        taskId,
        promptName,
        page_size: 100,
      });
      setPromptVersions(response.data.versions.filter(v => !v.deleted_at));
    } catch (error) {
      console.error("Failed to load prompt versions:", error);
    } finally {
      setLoadingPromptVersions(false);
    }
  };

  const loadDatasets = async () => {
    if (!api) return;
    try {
      setLoadingDatasets(true);
      const response = await api.api.getDatasetsApiV2DatasetsSearchGet({
        page_size: 100,
      });
      setDatasets(response.data.datasets);
    } catch (error) {
      console.error("Failed to load datasets:", error);
    } finally {
      setLoadingDatasets(false);
    }
  };

  const loadDatasetVersions = async (datasetId: string) => {
    if (!api) return;
    try {
      setLoadingDatasetVersions(true);
      const response = await api.api.getDatasetVersionsApiV2DatasetsDatasetIdVersionsGet({
        datasetId,
        page_size: 100,
      });
      const versions = response.data.versions;
      setDatasetVersions(versions);

      // Set to highest version number
      if (versions.length > 0) {
        const maxVersion = Math.max(...versions.map(v => v.version_number));
        setFormData(prev => ({
          ...prev,
          datasetVersion: maxVersion
        }));

        // Load columns for the latest version
        const latestVersion = versions.find(v => v.version_number === maxVersion);
        if (latestVersion) {
          setDatasetColumns(latestVersion.column_names);
        }
      }
    } catch (error) {
      console.error("Failed to load dataset versions:", error);
    } finally {
      setLoadingDatasetVersions(false);
    }
  };

  const loadEvaluators = async () => {
    if (!taskId || !api) return;
    try {
      setLoadingEvaluators(true);
      const response = await api.api.getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet({
        taskId,
        page_size: 100,
      });
      setEvaluators(response.data.llm_metadata);
    } catch (error) {
      console.error("Failed to load evaluators:", error);
    } finally {
      setLoadingEvaluators(false);
    }
  };

  const loadEvaluatorVersions = async (evalName: string) => {
    if (!taskId || !api) return;
    try {
      const response = await api.api.getAllLlmEvalVersionsApiV1TasksTaskIdLlmEvalsEvalNameVersionsGet({
        taskId,
        evalName,
        page_size: 100,
      });
      const versions = response.data.versions.filter(v => !v.deleted_at);
      setEvaluatorVersions(prev => ({
        ...prev,
        [evalName]: versions,
      }));

      // Set to highest version number
      if (versions.length > 0) {
        const maxVersion = Math.max(...versions.map(v => v.version));
        setCurrentEvaluatorVersion(maxVersion);
      }
    } catch (error) {
      console.error("Failed to load evaluator versions:", error);
    }
  };

  const loadPromptVariables = async () => {
    if (!taskId || !api || !selectedPromptName || formData.promptVersions.length === 0) return;
    try {
      setLoadingPromptDetails(true);
      // Fetch details for the first selected version to get variables
      const firstVersion = formData.promptVersions[0];
      const response = await api.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
        firstVersion.promptName,
        String(firstVersion.version),
        taskId
      );
      if (response.data.variables) {
        setPromptVariables(response.data.variables);
      }
    } catch (error) {
      console.error("Failed to load prompt variables:", error);
    } finally {
      setLoadingPromptDetails(false);
    }
  };

  const loadEvalVariablesForEvaluator = async (evalName: string, evalVersion: number) => {
    if (!taskId || !api) return;
    try {
      setLoadingEvalDetails(true);
      const response = await api.api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(
        evalName,
        String(evalVersion),
        taskId
      );
      if (response.data.variables) {
        setEvalVariables(prev => ({
          ...prev,
          [`${evalName}-${evalVersion}`]: {
            name: evalName,
            version: evalVersion,
            variables: response.data.variables || [],
          },
        }));
      }
    } catch (error) {
      console.error("Failed to load eval variables:", error);
    } finally {
      setLoadingEvalDetails(false);
    }
  };

  const handleAddPromptVersion = (version: number) => {
    if (!selectedPromptName) return;

    const existingIndex = formData.promptVersions.findIndex(
      pv => pv.promptName === selectedPromptName && pv.version === version
    );

    if (existingIndex >= 0) {
      // Remove if already selected (toggle off)
      setFormData(prev => ({
        ...prev,
        promptVersions: prev.promptVersions.filter((_, i) => i !== existingIndex),
      }));

      // Also remove from visible older versions if it's not in the top 5
      const top5Versions = promptVersions.slice(0, 5).map(v => v.version);
      if (!top5Versions.includes(version)) {
        setVisibleOlderVersions(prev => prev.filter(v => v !== version));
      }
    } else {
      // Add if not selected (toggle on)
      setFormData(prev => ({
        ...prev,
        promptVersions: [...prev.promptVersions, { promptName: selectedPromptName, version }],
      }));
    }
  };

  const handleAddEvaluator = async () => {
    if (!currentEvaluatorName || !currentEvaluatorVersion) return;

    const alreadyAdded = formData.evaluators.some(
      e => e.name === currentEvaluatorName && e.version === currentEvaluatorVersion
    );

    if (!alreadyAdded) {
      setFormData(prev => ({
        ...prev,
        evaluators: [...prev.evaluators, { name: currentEvaluatorName, version: currentEvaluatorVersion as number }],
      }));
      setCurrentEvaluatorName("");
      setCurrentEvaluatorVersion("");
    }
  };

  const handleRemoveEvaluator = (index: number) => {
    setFormData(prev => ({
      ...prev,
      evaluators: prev.evaluators.filter((_, i) => i !== index),
    }));
  };

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof ExperimentFormData | "general", string>> = {};

    if (!formData.name.trim()) {
      newErrors.name = "Experiment name is required";
    }

    if (formData.promptVersions.length === 0) {
      newErrors.promptVersions = "At least one prompt version is required";
    }

    if (!formData.datasetId) {
      newErrors.datasetId = "Dataset is required";
    }

    if (!formData.datasetVersion) {
      newErrors.datasetVersion = "Dataset version is required";
    }

    if (formData.evaluators.length === 0) {
      newErrors.evaluators = "At least one evaluator is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    try {
      setIsSubmitting(true);
      // Transform formData to match API expectations
      // The parent component will handle the actual API call
      await onSubmit(formData);
      // Reset form on success
      setFormData({
        name: "",
        description: "",
        promptVersions: [],
        datasetId: "",
        datasetVersion: "",
        evaluators: [],
        promptVariableMappings: {},
        evalVariableMappings: [],
      });
      setSelectedPromptName("");
      setVisibleOlderVersions([]);
      setCurrentEvaluatorName("");
      setCurrentEvaluatorVersion("");
      setPromptVariables([]);
      setEvalVariables({});
      setDatasetColumns([]);
      setCurrentStep(0);
      setCurrentEvalIndex(0);
      setCompletedSteps(new Set());
      setErrors({});
      onClose();
    } catch (error) {
      console.error("Failed to create experiment:", error);
      setErrors({ general: "Failed to create experiment. Please try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    // Reset form on cancel
    setFormData({
      name: "",
      description: "",
      promptVersions: [],
      datasetId: "",
      datasetVersion: "",
      evaluators: [],
      promptVariableMappings: {},
      evalVariableMappings: [],
    });
    setSelectedPromptName("");
    setVisibleOlderVersions([]);
    setCurrentEvaluatorName("");
    setCurrentEvaluatorVersion("");
    setPromptVariables([]);
    setEvalVariables({});
    setDatasetColumns([]);
    setCurrentStep(0);
    setCurrentEvalIndex(0);
    setCompletedSteps(new Set());
    setErrors({});
    onClose();
  };

  // Step navigation - always show 3 high-level steps
  const getStepLabels = () => {
    return ["Experiment Info", "Configure Prompts", "Configure Evals"];
  };

  const canProceedFromStep = (step: number): boolean => {
    switch (step) {
      case 0:
        // Experiment info step - need basic info, prompt versions, dataset, and evaluators
        return !!(
          formData.name.trim() &&
          formData.promptVersions.length > 0 &&
          formData.datasetId &&
          formData.datasetVersion &&
          formData.evaluators.length > 0
        );
      case 1:
        // Configure prompt variables - need all mappings
        if (!formData.promptVariableMappings) return false;
        return promptVariables.every(varName => !!formData.promptVariableMappings![varName]);
      case 2:
        // Configure evals - need all mappings for ALL evaluators
        if (!formData.evalVariableMappings || formData.evaluators.length === 0) return false;

        return formData.evaluators.every(evaluator => {
          const evalMappings = formData.evalVariableMappings?.find(
            m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
          );
          if (!evalMappings) return false;

          const evalKey = `${evaluator.name}-${evaluator.version}`;
          const evalVars = evalVariables[evalKey]?.variables || [];
          return evalVars.every(varName => !!evalMappings.mappings[varName]);
        });
      default:
        return false;
    }
  };

  const handleNext = async () => {
    if (currentStep === 0) {
      // Load prompt variables before moving to step 1
      if (!taskId || !api || formData.promptVersions.length === 0) return;

      try {
        setLoadingPromptDetails(true);
        const firstVersion = formData.promptVersions[0];
        const response = await api.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
          firstVersion.promptName,
          String(firstVersion.version),
          taskId
        );

        const vars = response.data.variables || [];
        setPromptVariables(vars);

        // Initialize prompt variable mappings with auto-matching
        if (datasetColumns.length > 0 && vars.length > 0) {
          const mappings: PromptVariableMappings = {};
          vars.forEach(varName => {
            const matchingColumn = datasetColumns.find(col => col === varName);
            if (matchingColumn) {
              mappings[varName] = matchingColumn;
            }
          });
          setFormData(prev => ({ ...prev, promptVariableMappings: mappings }));
        }
      } catch (error) {
        console.error("Failed to load prompt variables:", error);
      } finally {
        setLoadingPromptDetails(false);
      }
      setCompletedSteps(prev => new Set(prev).add(currentStep));
      setCurrentStep(prev => prev + 1);
    } else if (currentStep === 1) {
      // Load eval variables for first evaluator before moving to step 2
      if (formData.evaluators.length > 0) {
        const firstEval = formData.evaluators[0];
        await loadEvalVariablesForEvaluator(firstEval.name, firstEval.version);
        setCurrentEvalIndex(0);
      }
      setCompletedSteps(prev => new Set(prev).add(currentStep));
      setCurrentStep(prev => prev + 1);
    } else if (currentStep === 2) {
      // Within evals step, navigate between evaluators
      const nextEvalIndex = currentEvalIndex + 1;
      if (nextEvalIndex < formData.evaluators.length) {
        // Move to next evaluator within step 2
        const nextEval = formData.evaluators[nextEvalIndex];
        await loadEvalVariablesForEvaluator(nextEval.name, nextEval.version);
        setCurrentEvalIndex(nextEvalIndex);
      } else {
        // All evaluators configured, can submit
        setCompletedSteps(prev => new Set(prev).add(currentStep));
      }
    }
  };

  const handleBack = () => {
    if (currentStep === 2 && currentEvalIndex > 0) {
      // Within evals step, go back to previous evaluator
      setCurrentEvalIndex(prev => prev - 1);
    } else {
      // Go back to previous main step
      setCurrentStep(prev => prev - 1);
      if (currentStep === 2) {
        // Reset eval index when leaving step 2
        setCurrentEvalIndex(0);
      }
    }
  };

  const isLastStep = () => {
    // We're at the last step when on step 2 and on the last evaluator
    return currentStep === 2 && currentEvalIndex === formData.evaluators.length - 1;
  };

  // Check if we can proceed from current eval in step 2
  const canProceedFromCurrentEval = (): boolean => {
    if (currentStep !== 2) return true;

    const evaluator = formData.evaluators[currentEvalIndex];
    if (!evaluator) return false;

    const evalMappings = formData.evalVariableMappings?.find(
      m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
    );
    if (!evalMappings) return false;

    const evalKey = `${evaluator.name}-${evaluator.version}`;
    const evalVars = evalVariables[evalKey]?.variables || [];
    return evalVars.every(varName => !!evalMappings.mappings[varName]);
  };

  // Render step content
  const renderStepContent = () => {
    if (currentStep === 0) {
      return renderExperimentInfoStep();
    } else if (currentStep === 1) {
      return renderPromptVariableMappingStep();
    } else {
      return renderEvalVariableMappingStep(currentEvalIndex);
    }
  };

  const renderExperimentInfoStep = () => (
    <Box className="flex flex-col gap-4 mt-2">
      {/* Basic Info */}
          <TextField
            label="Experiment Name"
            value={formData.name}
            onChange={(e) => {
              setFormData(prev => ({ ...prev, name: e.target.value }));
              if (errors.name) setErrors(prev => ({ ...prev, name: undefined }));
            }}
            error={!!errors.name}
            helperText={errors.name}
            fullWidth
            required
            placeholder="e.g., Customer Support Tone Variations"
            autoFocus
          />

          <TextField
            label="Description"
            value={formData.description}
            onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
            fullWidth
            multiline
            rows={2}
            placeholder="Describe the purpose of this experiment"
          />

          {/* Prompt Selection */}
          <Box className="border border-gray-300 rounded p-4">
            <Typography variant="subtitle1" className="font-semibold mb-3">
              Prompt Versions *
            </Typography>

            <Box className="flex gap-2 mb-3">
              <Autocomplete
                options={prompts}
                getOptionLabel={(option) => option.name}
                value={prompts.find(p => p.name === selectedPromptName) || null}
                onChange={(_, value) => {
                  setSelectedPromptName(value?.name || "");
                  setPromptVersions([]);
                  setVisibleOlderVersions([]);
                }}
                loading={loadingPrompts}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Prompt"
                    placeholder="Search prompts..."
                  />
                )}
                className="flex-1"
              />
            </Box>

            {selectedPromptName && (
              <Box className="mb-3">
                <Typography variant="body2" className="text-gray-600 mb-2">
                  Select versions to include (click to toggle):
                </Typography>
                {loadingPromptVersions ? (
                  <CircularProgress size={24} />
                ) : (
                  <>
                    <Box className="flex flex-wrap gap-2 mb-3">
                      {(() => {
                        // Get the 5 most recent versions
                        const recentVersions = promptVersions.slice(0, 5);
                        // Get older versions that have been explicitly added
                        const olderVersionsToShow = promptVersions.filter(v =>
                          visibleOlderVersions.includes(v.version) &&
                          !recentVersions.some(rv => rv.version === v.version)
                        );
                        const allVisibleVersions = [...recentVersions, ...olderVersionsToShow];

                        return allVisibleVersions.map((version) => (
                          <Chip
                            key={version.version}
                            label={`v${version.version}`}
                            onClick={() => handleAddPromptVersion(version.version)}
                            color={
                              formData.promptVersions.some(
                                pv => pv.promptName === selectedPromptName && pv.version === version.version
                              )
                                ? "primary"
                                : "default"
                            }
                            variant={
                              formData.promptVersions.some(
                                pv => pv.promptName === selectedPromptName && pv.version === version.version
                              )
                                ? "filled"
                                : "outlined"
                            }
                          />
                        ));
                      })()}
                    </Box>

                    {promptVersions.length > 5 && (
                      <FormControl size="small" className="w-64">
                        <InputLabel>Add older version</InputLabel>
                        <Select
                          value=""
                          onChange={(e) => {
                            const version = Number(e.target.value);
                            if (version && !visibleOlderVersions.includes(version)) {
                              setVisibleOlderVersions(prev => [...prev, version]);
                              handleAddPromptVersion(version);
                            }
                          }}
                          label="Add older version"
                        >
                          {promptVersions.slice(5).map((version) => (
                            <MenuItem
                              key={version.version}
                              value={version.version}
                              disabled={visibleOlderVersions.includes(version.version)}
                            >
                              v{version.version}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    )}
                  </>
                )}
              </Box>
            )}

            {errors.promptVersions && (
              <Typography variant="caption" className="text-red-600 mt-2">
                {errors.promptVersions}
              </Typography>
            )}
          </Box>

          {/* Dataset Selection */}
          <Box className="border border-gray-300 rounded p-4">
            <Typography variant="subtitle1" className="font-semibold mb-3">
              Dataset *
            </Typography>

            <Box className="flex gap-2 mb-3">
              <Autocomplete
                options={datasets}
                getOptionLabel={(option) => option.name}
                value={datasets.find(d => d.id === formData.datasetId) || null}
                onChange={(_, value) => {
                  setFormData(prev => ({
                    ...prev,
                    datasetId: value?.id || "",
                  }));
                  if (value?.id) {
                    loadDatasetVersions(value.id);
                  } else {
                    setDatasetVersions([]);
                  }
                  if (errors.datasetId) setErrors(prev => ({ ...prev, datasetId: undefined }));
                }}
                loading={loadingDatasets}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Dataset"
                    error={!!errors.datasetId}
                    placeholder="Search datasets..."
                  />
                )}
                renderOption={(props, option) => (
                  <li {...props}>
                    <Box>
                      <Typography variant="body2">{option.name}</Typography>
                      {option.description && (
                        <Typography variant="caption" className="text-gray-600">
                          {option.description}
                        </Typography>
                      )}
                    </Box>
                  </li>
                )}
                className="flex-1"
              />

              <FormControl className="w-40">
                <InputLabel>Version</InputLabel>
                <Select
                  value={formData.datasetVersion}
                  onChange={(e) => {
                    const versionNumber = e.target.value as number;
                    setFormData(prev => ({
                      ...prev,
                      datasetVersion: versionNumber
                    }));
                    // Update columns when version changes
                    const selectedVersion = datasetVersions.find(v => v.version_number === versionNumber);
                    if (selectedVersion) {
                      setDatasetColumns(selectedVersion.column_names);
                    }
                  }}
                  label="Version"
                  disabled={!formData.datasetId || loadingDatasetVersions}
                  displayEmpty={false}
                >
                  {datasetVersions.map((version) => (
                    <MenuItem key={version.version_number} value={version.version_number}>
                      v{version.version_number}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            {(errors.datasetId || errors.datasetVersion) && (
              <Typography variant="caption" className="text-red-600">
                {errors.datasetId || errors.datasetVersion}
              </Typography>
            )}
          </Box>

          {/* Evaluator Selection */}
          <Box className="border border-gray-300 rounded p-4">
            <Typography variant="subtitle1" className="font-semibold mb-3">
              Evaluators *
            </Typography>

            <Box className="flex gap-2 mb-3">
              <FormControl className="flex-1">
                <InputLabel>Evaluator</InputLabel>
                <Select
                  value={currentEvaluatorName}
                  onChange={async (e) => {
                    const evalName = e.target.value;
                    setCurrentEvaluatorName(evalName);
                    setCurrentEvaluatorVersion("");
                    if (evalName && !evaluatorVersions[evalName]) {
                      await loadEvaluatorVersions(evalName);
                    }
                  }}
                  label="Evaluator"
                >
                  {evaluators.map((evaluator) => (
                    <MenuItem key={evaluator.name} value={evaluator.name}>
                      {evaluator.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <FormControl className="flex-1">
                <InputLabel>Version</InputLabel>
                <Select
                  value={currentEvaluatorVersion}
                  onChange={(e) => setCurrentEvaluatorVersion(e.target.value as number)}
                  label="Version"
                  disabled={!currentEvaluatorName}
                >
                  {currentEvaluatorName &&
                    evaluatorVersions[currentEvaluatorName]?.map((version) => (
                      <MenuItem key={version.version} value={version.version}>
                        v{version.version}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>

              <Button
                variant="outlined"
                onClick={handleAddEvaluator}
                disabled={!currentEvaluatorName || !currentEvaluatorVersion}
                startIcon={<AddIcon />}
              >
                Add
              </Button>
            </Box>

            {formData.evaluators.length > 0 && (
              <Box>
                <Typography variant="body2" className="text-gray-600 mb-2">
                  Selected evaluators:
                </Typography>
                <Box className="flex flex-col gap-2">
                  {formData.evaluators.map((evaluator, index) => (
                    <Box
                      key={`${evaluator.name}-${evaluator.version}`}
                      className="flex items-center justify-between bg-gray-50 p-2 rounded"
                    >
                      <Typography variant="body2">
                        {evaluator.name} v{evaluator.version}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveEvaluator(index)}
                        className="text-red-600"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ))}
                </Box>
              </Box>
            )}

            {errors.evaluators && (
              <Typography variant="caption" className="text-red-600 mt-2">
                {errors.evaluators}
              </Typography>
            )}
          </Box>

      {errors.general && (
        <Typography variant="body2" className="text-red-600">
          {errors.general}
        </Typography>
      )}
    </Box>
  );

  const renderPromptVariableMappingStep = () => (
    <Box className="flex flex-col gap-4 mt-2">
      <Typography variant="body1" className="text-gray-700">
        Map each prompt variable to a dataset column. Variables that match column names exactly have been auto-filled.
      </Typography>

      {loadingPromptDetails ? (
        <Box className="flex justify-center p-4">
          <CircularProgress />
        </Box>
      ) : promptVariables.length === 0 ? (
        <Typography variant="body2" className="text-gray-600 italic">
          No variables found for this prompt.
        </Typography>
      ) : (
        <Box className="flex flex-col gap-3">
          {promptVariables.map((varName) => (
            <FormControl key={varName} fullWidth>
              <InputLabel required>{varName}</InputLabel>
              <Select
                value={formData.promptVariableMappings?.[varName] || ""}
                onChange={(e) => {
                  setFormData(prev => ({
                    ...prev,
                    promptVariableMappings: {
                      ...prev.promptVariableMappings,
                      [varName]: e.target.value,
                    },
                  }));
                }}
                label={varName}
              >
                <MenuItem value="">
                  <em>Select a column</em>
                </MenuItem>
                {datasetColumns.map((column) => (
                  <MenuItem key={column} value={column}>
                    {column}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ))}
        </Box>
      )}
    </Box>
  );

  const renderEvalVariableMappingStep = (evalIndex: number) => {
    const evaluator = formData.evaluators[evalIndex];
    if (!evaluator) return null;

    const evalKey = `${evaluator.name}-${evaluator.version}`;
    const evalVars = evalVariables[evalKey]?.variables || [];
    const currentMappings = formData.evalVariableMappings?.find(
      m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
    );

    return (
      <Box className="flex flex-col gap-4 mt-2">
        <Box>
          <Typography variant="body2" className="text-gray-500 mb-1">
            Evaluator {evalIndex + 1} of {formData.evaluators.length}
          </Typography>
          <Typography variant="body1" className="text-gray-700">
            Map each variable for <strong>{evaluator.name} (v{evaluator.version})</strong> to either a dataset column or the experiment output.
          </Typography>
        </Box>

        {loadingEvalDetails ? (
          <Box className="flex justify-center p-4">
            <CircularProgress />
          </Box>
        ) : evalVars.length === 0 ? (
          <Typography variant="body2" className="text-gray-600 italic">
            No variables found for this evaluator.
          </Typography>
        ) : (
          <Box className="flex flex-col gap-4">
            {evalVars.map((varName) => {
              const mapping = currentMappings?.mappings[varName];
              const sourceType = mapping?.sourceType || "dataset_column";

              return (
                <Box key={varName} className="border border-gray-300 rounded p-3">
                  <Typography variant="subtitle2" className="font-medium mb-2">
                    {varName} *
                  </Typography>

                  <Box className="flex gap-2 mb-2">
                    <Button
                      variant={sourceType === "dataset_column" ? "contained" : "outlined"}
                      size="small"
                      onClick={() => {
                        const newMappings = formData.evalVariableMappings || [];
                        const existingIndex = newMappings.findIndex(
                          m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
                        );

                        const updatedMapping = {
                          evalName: evaluator.name,
                          evalVersion: evaluator.version,
                          mappings: {
                            ...(existingIndex >= 0 ? newMappings[existingIndex].mappings : {}),
                            [varName]: {
                              sourceType: "dataset_column" as VariableSourceType,
                              datasetColumn: mapping?.datasetColumn || "",
                            },
                          },
                        };

                        if (existingIndex >= 0) {
                          newMappings[existingIndex] = updatedMapping;
                        } else {
                          newMappings.push(updatedMapping);
                        }

                        setFormData(prev => ({
                          ...prev,
                          evalVariableMappings: newMappings,
                        }));
                      }}
                    >
                      Dataset Column
                    </Button>
                    <Button
                      variant={sourceType === "experiment_output" ? "contained" : "outlined"}
                      size="small"
                      onClick={() => {
                        const newMappings = formData.evalVariableMappings || [];
                        const existingIndex = newMappings.findIndex(
                          m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
                        );

                        const updatedMapping = {
                          evalName: evaluator.name,
                          evalVersion: evaluator.version,
                          mappings: {
                            ...(existingIndex >= 0 ? newMappings[existingIndex].mappings : {}),
                            [varName]: {
                              sourceType: "experiment_output" as VariableSourceType,
                              jsonPath: mapping?.jsonPath || "",
                            },
                          },
                        };

                        if (existingIndex >= 0) {
                          newMappings[existingIndex] = updatedMapping;
                        } else {
                          newMappings.push(updatedMapping);
                        }

                        setFormData(prev => ({
                          ...prev,
                          evalVariableMappings: newMappings,
                        }));
                      }}
                    >
                      Experiment Output
                    </Button>
                  </Box>

                  {sourceType === "dataset_column" ? (
                    <FormControl fullWidth size="small">
                      <InputLabel>Dataset Column</InputLabel>
                      <Select
                        value={mapping?.datasetColumn || ""}
                        onChange={(e) => {
                          const newMappings = formData.evalVariableMappings || [];
                          const existingIndex = newMappings.findIndex(
                            m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
                          );

                          const updatedMapping = {
                            evalName: evaluator.name,
                            evalVersion: evaluator.version,
                            mappings: {
                              ...(existingIndex >= 0 ? newMappings[existingIndex].mappings : {}),
                              [varName]: {
                                sourceType: "dataset_column" as VariableSourceType,
                                datasetColumn: e.target.value,
                              },
                            },
                          };

                          if (existingIndex >= 0) {
                            newMappings[existingIndex] = updatedMapping;
                          } else {
                            newMappings.push(updatedMapping);
                          }

                          setFormData(prev => ({
                            ...prev,
                            evalVariableMappings: newMappings,
                          }));
                        }}
                        label="Dataset Column"
                      >
                        <MenuItem value="">
                          <em>Select a column</em>
                        </MenuItem>
                        {datasetColumns.map((column) => (
                          <MenuItem key={column} value={column}>
                            {column}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  ) : (
                    <TextField
                      fullWidth
                      size="small"
                      label="JSON Path (optional)"
                      placeholder="e.g., .response.data"
                      value={mapping?.jsonPath || ""}
                      onChange={(e) => {
                        const newMappings = formData.evalVariableMappings || [];
                        const existingIndex = newMappings.findIndex(
                          m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
                        );

                        const updatedMapping = {
                          evalName: evaluator.name,
                          evalVersion: evaluator.version,
                          mappings: {
                            ...(existingIndex >= 0 ? newMappings[existingIndex].mappings : {}),
                            [varName]: {
                              sourceType: "experiment_output" as VariableSourceType,
                              jsonPath: e.target.value,
                            },
                          },
                        };

                        if (existingIndex >= 0) {
                          newMappings[existingIndex] = updatedMapping;
                        } else {
                          newMappings.push(updatedMapping);
                        }

                        setFormData(prev => ({
                          ...prev,
                          evalVariableMappings: newMappings,
                        }));
                      }}
                    />
                  )}
                </Box>
              );
            })}
          </Box>
        )}
      </Box>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={handleCancel}
      maxWidth="md"
      fullWidth
      aria-labelledby="create-experiment-dialog-title"
    >
      <DialogTitle id="create-experiment-dialog-title">
        Create New Experiment
      </DialogTitle>
      <DialogContent>
        <Box className="mb-4">
          <Stepper activeStep={currentStep} alternativeLabel>
            {getStepLabels().map((label, index) => (
              <Step key={label} completed={completedSteps.has(index)}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {renderStepContent()}
      </DialogContent>
      <DialogActions className="px-6 pb-4">
        <Button onClick={handleCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        {(currentStep > 0 || currentEvalIndex > 0) && (
          <Button onClick={handleBack} disabled={isSubmitting}>
            Back
          </Button>
        )}
        {!isLastStep() ? (
          <Button
            onClick={handleNext}
            variant="contained"
            color="primary"
            disabled={
              (currentStep === 2 ? !canProceedFromCurrentEval() : !canProceedFromStep(currentStep)) ||
              isSubmitting
            }
          >
            {currentStep === 0 ? "Configure Prompts" :
             currentStep === 1 ? "Configure Evals" :
             "Next Evaluator"}
          </Button>
        ) : (
          <Button
            onClick={handleSubmit}
            variant="contained"
            color="primary"
            disabled={!canProceedFromCurrentEval() || isSubmitting}
            startIcon={isSubmitting ? <CircularProgress size={16} /> : null}
          >
            {isSubmitting ? "Creating..." : "Create Experiment"}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};
