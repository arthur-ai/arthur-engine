import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
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

import { EvalFormModalProps } from "./types";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { CreateEvalRequest, LLMEval, ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";

const EvalFormModal = ({ open, onClose, onSubmit, isLoading = false }: EvalFormModalProps) => {
  const apiClient = useApi();
  const { task } = useTask();
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
    } catch (err) {
      console.error("Failed to create eval:", err);
      setError(err instanceof Error ? err.message : "Failed to create eval. Please try again.");
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

  const handleEvalNameChange = useCallback(
    (_event: React.SyntheticEvent<Element, Event>, newValue: string | null, reason: string) => {
      const selectedName = newValue || "";

      // If cleared or empty, reset all fields
      if (!selectedName || reason === "clear") {
        setEvalName("");
        setInstructions("");
        setModelProvider(enabledProviders.length > 0 ? enabledProviders[0] : "");
        setModelName("");
        prevEvalNameRef.current = "";
        return;
      }

      prevEvalNameRef.current = selectedName;

      // Only auto-fill when explicitly selecting from dropdown or pressing enter
      if (existingEvalNames.includes(selectedName) && (reason === "selectOption" || reason === "createOption")) {
        fetchLatestEvalVersion(selectedName);
      }
    },
    [fetchLatestEvalVersion, enabledProviders, existingEvalNames]
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
              <Autocomplete
                freeSolo
                options={existingEvalNames}
                value={evalName}
                inputValue={evalName}
                onChange={handleEvalNameChange}
                onInputChange={(_event, newValue) => {
                  setEvalName(newValue);
                }}
                onClose={() => {
                  if (evalName && existingEvalNames.includes(evalName) && prevEvalNameRef.current !== evalName) {
                    prevEvalNameRef.current = evalName;
                    fetchLatestEvalVersion(evalName);
                  }
                }}
                disabled={isLoading}
                forcePopupIcon={true}
                filterOptions={(options, state) => {
                  if (!state.inputValue) {
                    return options;
                  }
                  const filtered = options.filter((option) =>
                    option.toLowerCase().includes(state.inputValue.toLowerCase())
                  );
                  // Add a placeholder message when no matches
                  if (filtered.length === 0) {
                    return ["__NO_OPTIONS__"];
                  }
                  return filtered;
                }}
                getOptionDisabled={(option) => option === "__NO_OPTIONS__"}
                renderOption={(props, option) => {
                  const { key, ...otherProps } = props;
                  return (
                    <li key={key} {...otherProps} style={option === "__NO_OPTIONS__" ? { cursor: "default" } : undefined}>
                      {option === "__NO_OPTIONS__" ? "No existing evals" : option}
                    </li>
                  );
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Enter eval name or select existing..."
                    required
                    size="small"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && evalName && existingEvalNames.includes(evalName)) {
                        e.preventDefault();
                        fetchLatestEvalVersion(evalName);
                      }
                    }}
                    onBlur={() => {
                      if (evalName && existingEvalNames.includes(evalName)) {
                        fetchLatestEvalVersion(evalName);
                      }
                    }}
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
              <TextField
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
