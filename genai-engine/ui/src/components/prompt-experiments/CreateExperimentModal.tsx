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
  LLMEvalsVersionResponse,
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
  version: number | "latest";
}

export interface ExperimentFormData {
  name: string;
  description: string;
  promptVersions: PromptVersionSelection[];
  datasetId: string;
  datasetVersion: number | "latest";
  evaluators: EvaluatorSelection[];
}

export const CreateExperimentModal: React.FC<CreateExperimentModalProps> = ({
  open,
  onClose,
  onSubmit,
}) => {
  const { id: taskId } = useParams<{ id: string }>();
  const api = useApi();

  // Form state
  const [formData, setFormData] = useState<ExperimentFormData>({
    name: "",
    description: "",
    promptVersions: [],
    datasetId: "",
    datasetVersion: "latest",
    evaluators: [],
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
  const [loadingDatasets, setLoadingDatasets] = useState(false);
  const [loadingDatasetVersions, setLoadingDatasetVersions] = useState(false);

  // Evaluators state
  const [evaluators, setEvaluators] = useState<LLMGetAllMetadataResponse[]>([]);
  const [evaluatorVersions, setEvaluatorVersions] = useState<Record<string, LLMEvalsVersionResponse[]>>({});
  const [loadingEvaluators, setLoadingEvaluators] = useState(false);
  const [currentEvaluatorName, setCurrentEvaluatorName] = useState<string>("");
  const [currentEvaluatorVersion, setCurrentEvaluatorVersion] = useState<number | "latest" | "">("latest");

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
      setDatasetVersions(response.data.versions);
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
      setEvaluatorVersions(prev => ({
        ...prev,
        [evalName]: response.data.versions.filter(v => !v.deleted_at),
      }));
    } catch (error) {
      console.error("Failed to load evaluator versions:", error);
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
    if (!currentEvaluatorName || currentEvaluatorVersion === "") return;

    const alreadyAdded = formData.evaluators.some(
      e => e.name === currentEvaluatorName && e.version === currentEvaluatorVersion
    );

    if (!alreadyAdded) {
      setFormData(prev => ({
        ...prev,
        evaluators: [...prev.evaluators, { name: currentEvaluatorName, version: currentEvaluatorVersion as (number | "latest") }],
      }));
      setCurrentEvaluatorName("");
      setCurrentEvaluatorVersion("latest");
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
      await onSubmit(formData);
      // Reset form on success
      setFormData({
        name: "",
        description: "",
        promptVersions: [],
        datasetId: "",
        datasetVersion: "latest",
        evaluators: [],
      });
      setSelectedPromptName("");
      setVisibleOlderVersions([]);
      setCurrentEvaluatorName("");
      setCurrentEvaluatorVersion("latest");
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
      datasetVersion: "latest",
      evaluators: [],
    });
    setSelectedPromptName("");
    setVisibleOlderVersions([]);
    setCurrentEvaluatorName("");
    setCurrentEvaluatorVersion("latest");
    setErrors({});
    onClose();
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
                            const version = e.target.value as number;
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
                    datasetVersion: "latest"
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
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    datasetVersion: e.target.value as (number | "latest")
                  }))}
                  label="Version"
                  disabled={!formData.datasetId || loadingDatasetVersions}
                >
                  <MenuItem value="latest">Latest</MenuItem>
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
                  onChange={(e) => setCurrentEvaluatorVersion(e.target.value as (number | "latest"))}
                  label="Version"
                  disabled={!currentEvaluatorName}
                >
                  <MenuItem value="latest">Latest</MenuItem>
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
                disabled={!currentEvaluatorName || currentEvaluatorVersion === ""}
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
                        {evaluator.name} {evaluator.version === "latest" ? "(Latest)" : `v${evaluator.version}`}
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
      </DialogContent>
      <DialogActions className="px-6 pb-4">
        <Button onClick={handleCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={isSubmitting}
          startIcon={isSubmitting ? <CircularProgress size={16} /> : null}
        >
          {isSubmitting ? "Creating..." : "Create Experiment"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
