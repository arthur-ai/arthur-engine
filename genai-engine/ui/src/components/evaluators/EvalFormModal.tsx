import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormLabel from "@mui/material/FormLabel";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useEvaluatorTemplates } from "./hooks/useEvaluatorTemplates";
import NunjucksHighlightedTextField from "./MustacheHighlightedTextField";
import { EvalFormModalProps } from "./types";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { CreateEvalRequest, LLMEval, ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";

const EvalFormModal = ({ open, onClose, onSubmit, isLoading = false }: EvalFormModalProps) => {
  const apiClient = useApi();
  const { task } = useTask();
  const evaluatorTemplates = useEvaluatorTemplates();
  const [evalName, setEvalName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [modelProvider, setModelProvider] = useState<ModelProvider | "">("");
  const [modelName, setModelName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enabledProviders, setEnabledProviders] = useState<ModelProvider[]>([]);
  const [availableModels, setAvailableModels] = useState<Map<ModelProvider, string[]>>(new Map());
  const [existingEvalNames, setExistingEvalNames] = useState<string[]>([]);
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedEvalNames = useRef(false);

  const fetchProviders = useCallback(async () => {
    if (hasFetchedProviders.current) {
      return;
    }

    if (!apiClient) {
      console.error("No api client");
      return;
    }

    hasFetchedProviders.current = true;
    try {
      const response = await apiClient.api.getModelProvidersApiV1ModelProvidersGet();
      const { data } = response;
      const providers = data.providers
        .filter((provider: ModelProviderResponse) => provider.enabled)
        .map((provider: ModelProviderResponse) => provider.provider);
      setEnabledProviders(providers);
    } catch (error) {
      console.error("Failed to fetch providers:", error);
      setError("Failed to load providers. Please try again.");
    }
  }, [apiClient]);

  const fetchAvailableModels = useCallback(async () => {
    if (hasFetchedAvailableModels.current || !apiClient || enabledProviders.length === 0) {
      return;
    }

    hasFetchedAvailableModels.current = true;

    // Fetch models for all enabled providers in parallel
    const modelPromises = enabledProviders.map(async (provider) => {
      try {
        const response = await apiClient.api.getModelProvidersAvailableModelsApiV1ModelProvidersProviderAvailableModelsGet(provider as ModelProvider);
        return { provider, models: response.data.available_models };
      } catch (error) {
        console.error(`Failed to fetch models for provider ${provider}:`, error);
        return { provider, models: [] };
      }
    });

    const results = await Promise.all(modelPromises);

    const newAvailableModels = new Map<ModelProvider, string[]>();
    results.forEach(({ provider, models }) => {
      newAvailableModels.set(provider, models);
    });

    setAvailableModels(newAvailableModels);
  }, [apiClient, enabledProviders]);

  const fetchExistingEvalNames = useCallback(async () => {
    if (hasFetchedEvalNames.current || !apiClient || !task?.id) {
      return;
    }

    hasFetchedEvalNames.current = true;
    try {
      const response = await apiClient.api.getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet({
        taskId: task.id,
        page: 0,
        page_size: 1000, // Fetch all eval names
      });
      const evalNames = response.data.llm_metadata.map((evalMeta) => evalMeta.name);
      setExistingEvalNames(evalNames);
    } catch (error) {
      console.error("Failed to fetch existing eval names:", error);
      // Don't show error to user, just fail silently
    }
  }, [apiClient, task?.id]);

  // Fetch providers and eval names when modal opens
  useEffect(() => {
    if (open) {
      // Reset refs when modal opens to allow fresh data fetch
      hasFetchedProviders.current = false;
      hasFetchedAvailableModels.current = false;
      hasFetchedEvalNames.current = false;
      fetchProviders();
      fetchExistingEvalNames();
    }
  }, [open, fetchProviders, fetchExistingEvalNames]);

  // Fetch available models when providers are loaded
  useEffect(() => {
    if (enabledProviders.length > 0) {
      fetchAvailableModels();
    }
  }, [enabledProviders, fetchAvailableModels]);

  // Set the first provider as the default provider
  useEffect(() => {
    if (enabledProviders.length > 0 && !modelProvider) {
      setModelProvider(enabledProviders[0]);
    }
  }, [enabledProviders, modelProvider]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!evalName.trim()) {
      setError("Eval name is required");
      return;
    }

    if (!instructions.trim()) {
      setError("Instructions are required");
      return;
    }

    if (!modelProvider) {
      setError("Model provider is required");
      return;
    }

    if (!modelName.trim()) {
      setError("Model name is required");
      return;
    }

    try {
      const data: CreateEvalRequest = {
        instructions: instructions.trim(),
        model_provider: modelProvider as ModelProvider,
        model_name: modelName.trim(),
      };

      await onSubmit(evalName.trim(), data);

      // Reset form on success
      setEvalName("");
      setInstructions("");
      setModelProvider(enabledProviders.length > 0 ? enabledProviders[0] : "");
      setModelName("");
      setError(null);
    } catch (err: any) {
      console.error("Failed to create eval:", err);

      // Extract error message from API response
      let errorMessage = "Failed to create eval. Please try again.";

      if (err?.response?.data?.detail) {
        // FastAPI HTTPException detail
        errorMessage = err.response.data.detail;
      } else if (err?.message) {
        errorMessage = err.message;
      } else if (typeof err === "string") {
        errorMessage = err;
      }

      setError(errorMessage);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setEvalName("");
      setInstructions("");
      setModelProvider(enabledProviders.length > 0 ? enabledProviders[0] : "");
      setModelName("");
      setError(null);
      onClose();
    }
  };

  const handleProviderChange = (_event: React.SyntheticEvent<Element, Event>, newValue: ModelProvider | null) => {
    setModelProvider(newValue || "");
    setModelName(""); // Clear model selection when provider changes
  };

  const handleModelChange = (_event: React.SyntheticEvent<Element, Event>, newValue: string | null) => {
    setModelName(newValue || "");
  };

  const fetchLatestEvalVersion = useCallback(
    async (evalName: string) => {
      if (!apiClient || !task?.id || !evalName) {
        return;
      }

      try {
        // Fetch the latest version using "latest" as the version parameter
        // API signature: (evalName, evalVersion, taskId)
        const evalResponse = await apiClient.api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(
          evalName,
          "latest" as any, // The API accepts "latest" as a special version string
          task.id
        );

        const evalData: LLMEval = evalResponse.data;

        // Populate form with the eval data
        setInstructions(evalData.instructions);
        setModelProvider(evalData.model_provider);
        setModelName(evalData.model_name);
      } catch (error) {
        console.error("Failed to fetch latest eval version:", error);
        // Don't show error to user, just fail silently
      }
    },
    [apiClient, task?.id]
  );

  const prevEvalNameRef = useRef("");

  // Create option objects that distinguish between templates and existing evals
  type EvalOption = {
    id: string;
    name: string;
    type: "template" | "existing";
    attribution?: string;
  };

  const allEvalNameOptions = useMemo(() => {
    const options: EvalOption[] = [];

    // Add templates
    evaluatorTemplates.forEach((template) => {
      options.push({
        id: `template-${template.name}`,
        name: template.name,
        type: "template",
        attribution: template.attribution,
      });
    });

    // Add existing evals
    existingEvalNames.forEach((name) => {
      options.push({
        id: `existing-${name}`,
        name: name,
        type: "existing",
      });
    });

    return options;
  }, [evaluatorTemplates, existingEvalNames]);

  const handleEvalNameChange = useCallback(
    (_event: React.SyntheticEvent<Element, Event>, newValue: EvalOption | string | null, reason: string) => {
      // If cleared or empty, reset all fields
      if (!newValue || reason === "clear") {
        setEvalName("");
        setInstructions("");
        setModelProvider(enabledProviders.length > 0 ? enabledProviders[0] : "");
        setModelName("");
        prevEvalNameRef.current = "";
        return;
      }

      // Handle both option objects and free text
      const selectedOption = typeof newValue === "string" ? null : newValue;
      const selectedName = typeof newValue === "string" ? newValue : newValue.name;

      prevEvalNameRef.current = selectedName;
      setEvalName(selectedName);

      // Only auto-fill when explicitly selecting from dropdown
      if (selectedOption && (reason === "selectOption" || reason === "createOption")) {
        if (selectedOption.type === "template") {
          // Populate from template
          const template = evaluatorTemplates.find((t) => t.name === selectedOption.name);
          if (template) {
            setInstructions(template.instructions);
          }
        } else if (selectedOption.type === "existing") {
          // Fetch latest version of existing eval
          fetchLatestEvalVersion(selectedOption.name);
        }
      }
    },
    [fetchLatestEvalVersion, enabledProviders, evaluatorTemplates]
  );

  const providerDisabled = enabledProviders.length === 0;
  const modelDisabled = modelProvider === "";
  const tooltipTitle = providerDisabled ? "No providers available. Please configure at least one provider." : "";
  const availableModelsForProvider = useMemo(() => availableModels.get(modelProvider as ModelProvider) || [], [availableModels, modelProvider]);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create New Eval</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}>
            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Eval Name
                </Typography>
              </FormLabel>
              <Autocomplete<EvalOption, false, false, true>
                freeSolo
                options={allEvalNameOptions}
                value={null}
                inputValue={evalName}
                onChange={handleEvalNameChange}
                onInputChange={(_event, newValue) => {
                  setEvalName(newValue);
                }}
                disabled={isLoading}
                forcePopupIcon={true}
                getOptionLabel={(option) => (typeof option === "string" ? option : option.name)}
                filterOptions={(options, state) => {
                  if (!state.inputValue) {
                    return options;
                  }
                  const filtered = options.filter((option) =>
                    option.name.toLowerCase().includes(state.inputValue.toLowerCase())
                  );
                  return filtered;
                }}
                renderOption={(props, option) => {
                  const { key, ...otherProps } = props;
                  const isTemplate = option.type === "template";
                  return (
                    <li key={key} {...otherProps} style={{ padding: "6px 16px" }}>
                      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1, flex: 1 }}>
                          <span>{option.name}</span>
                          {option.attribution && (
                            <Typography
                              variant="caption"
                              component="span"
                              sx={{
                                color: "rgba(0, 0, 0, 0.3)",
                                fontSize: "0.75rem",
                                fontWeight: 400,
                                fontStyle: "italic",
                                display: "inline"
                              }}
                            >
                              {option.attribution}
                            </Typography>
                          )}
                        </Box>
                        <Chip
                          label={isTemplate ? "Template" : "Existing"}
                          size="small"
                          color={isTemplate ? "primary" : "default"}
                          variant={isTemplate ? "filled" : "outlined"}
                          sx={{
                            height: 20,
                            fontSize: "0.7rem",
                            fontWeight: 500,
                            ml: 1,
                          }}
                        />
                      </Box>
                    </li>
                  );
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Enter eval name or select template/existing..."
                    required
                    size="small"
                    autoFocus
                  />
                )}
              />
            </FormControl>

            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Instructions
                </Typography>
              </FormLabel>
              <NunjucksHighlightedTextField
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Enter eval instructions..."
                disabled={isLoading}
                required
                multiline
                minRows={4}
                maxRows={10}
                size="small"
              />
            </FormControl>

            <Box sx={{ display: "flex", gap: 2 }}>
              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    Model Provider
                  </Typography>
                </FormLabel>
                <Tooltip title={tooltipTitle} placement="top-start" arrow>
                  <Autocomplete<ModelProvider>
                    options={enabledProviders}
                    value={modelProvider || null}
                    onChange={handleProviderChange}
                    disabled={providerDisabled || isLoading}
                    renderInput={(params) => (
                      <TextField {...params} label="Select Provider" variant="outlined" size="small" sx={{ backgroundColor: "white" }} />
                    )}
                  />
                </Tooltip>
              </FormControl>

              <FormControl fullWidth>
                <FormLabel>
                  <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                    Model Name
                  </Typography>
                </FormLabel>
                <Autocomplete
                  options={availableModelsForProvider}
                  value={modelName || null}
                  onChange={handleModelChange}
                  disabled={modelDisabled || isLoading}
                  renderInput={(params) => (
                    <TextField {...params} label="Select Model" variant="outlined" size="small" sx={{ backgroundColor: "white" }} />
                  )}
                />
              </FormControl>
            </Box>

            {error && (
              <Alert severity="error" onClose={() => setError(null)}>
                {error}
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isLoading || !evalName.trim() || !instructions.trim() || !modelProvider || !modelName.trim()}
            sx={{ minWidth: 120 }}
          >
            {isLoading ? "Saving..." : "Save Eval"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EvalFormModal;
