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

import { PromptFormModalProps } from "./types";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { CreateAgenticPromptRequest, AgenticPrompt, ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";

const PromptFormModal = ({ open, onClose, onSubmit, isLoading = false }: PromptFormModalProps) => {
  const apiClient = useApi();
  const { task } = useTask();
  const [promptName, setPromptName] = useState("");
  const [instructions, setInstructions] = useState("");
  const [modelProvider, setModelProvider] = useState<ModelProvider | "">("");
  const [modelName, setModelName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enabledProviders, setEnabledProviders] = useState<ModelProvider[]>([]);
  const [availableModels, setAvailableModels] = useState<Map<ModelProvider, string[]>>(new Map());
  const [existingPromptNames, setExistingPromptNames] = useState<string[]>([]);
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedPromptNames = useRef(false);

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

  const fetchExistingPromptNames = useCallback(async () => {
    if (hasFetchedPromptNames.current || !apiClient || !task?.id) {
      return;
    }

    hasFetchedPromptNames.current = true;
    try {
      const response = await apiClient.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
        taskId: task.id,
        page: 0,
        page_size: 1000, // Fetch all prompt names
      });
      const promptNames = response.data.llm_metadata.map((promptMeta) => promptMeta.name);
      setExistingPromptNames(promptNames);
    } catch (error) {
      console.error("Failed to fetch existing prompt names:", error);
      // Don't show error to user, just fail silently
    }
  }, [apiClient, task?.id]);

  // Fetch providers and prompt names when modal opens
  useEffect(() => {
    if (open) {
      // Reset refs when modal opens to allow fresh data fetch
      hasFetchedProviders.current = false;
      hasFetchedAvailableModels.current = false;
      hasFetchedPromptNames.current = false;
      fetchProviders();
      fetchExistingPromptNames();
    }
  }, [open, fetchProviders, fetchExistingPromptNames]);

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

    if (!promptName.trim()) {
      setError("Prompt name is required");
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
      const data: CreateAgenticPromptRequest = {
        messages: [{ role: "user", content: instructions.trim() }],
        model_provider: modelProvider as ModelProvider,
        model_name: modelName.trim(),
      };

      await onSubmit(promptName.trim(), data);

      // Reset form on success
      setPromptName("");
      setInstructions("");
      setModelProvider(enabledProviders.length > 0 ? enabledProviders[0] : "");
      setModelName("");
      setError(null);
    } catch (err) {
      console.error("Failed to create prompt:", err);
      setError(err instanceof Error ? err.message : "Failed to create prompt. Please try again.");
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setPromptName("");
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

  const fetchLatestPromptVersion = useCallback(
    async (promptName: string) => {
      if (!apiClient || !task?.id || !promptName) {
        return;
      }

      try {
        // Fetch the latest version using "latest" as the version parameter
        // API signature: (promptName, promptVersion, taskId)
        const promptResponse = await apiClient.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
          promptName,
          "latest" as any, // The API accepts "latest" as a special version string
          task.id
        );

        const promptData: AgenticPrompt = promptResponse.data;

        // Populate form with the prompt data
        // Convert messages array to instructions string (for simplicity, just use first message content)
        const firstMessage = promptData.messages?.[0];
        if (firstMessage && typeof firstMessage.content === "string") {
          setInstructions(firstMessage.content);
        }
        setModelProvider(promptData.model_provider);
        setModelName(promptData.model_name);
      } catch (error) {
        console.error("Failed to fetch latest prompt version:", error);
        // Don't show error to user, just fail silently
      }
    },
    [apiClient, task?.id]
  );

  const prevPromptNameRef = useRef("");

  const handlePromptNameChange = useCallback(
    (_event: React.SyntheticEvent<Element, Event>, newValue: string | null, reason: string) => {
      const selectedName = newValue || "";

      // If cleared or empty, reset all fields
      if (!selectedName || reason === "clear") {
        setPromptName("");
        setInstructions("");
        setModelProvider(enabledProviders.length > 0 ? enabledProviders[0] : "");
        setModelName("");
        prevPromptNameRef.current = "";
        return;
      }

      // Update promptName
      setPromptName(selectedName);
      prevPromptNameRef.current = selectedName;

      // Always fetch when selectOption
      if (existingPromptNames.includes(selectedName)) {
        fetchLatestPromptVersion(selectedName);
      }
    },
    [fetchLatestPromptVersion, enabledProviders, existingPromptNames]
  );

  // Watch for when promptName matches an existing prompt (for when onChange doesn't fire)
  useEffect(() => {
    if (promptName && existingPromptNames.includes(promptName) && prevPromptNameRef.current !== promptName) {
      prevPromptNameRef.current = promptName;
      fetchLatestPromptVersion(promptName);
    }
  }, [promptName, existingPromptNames, fetchLatestPromptVersion]);

  const providerDisabled = enabledProviders.length === 0;
  const modelDisabled = modelProvider === "";
  const tooltipTitle = providerDisabled ? "No providers available. Please configure at least one provider." : "";
  const availableModelsForProvider = useMemo(() => availableModels.get(modelProvider as ModelProvider) || [], [availableModels, modelProvider]);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create New Prompt</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}>
            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Prompt Name
                </Typography>
              </FormLabel>
              <Autocomplete
                freeSolo
                options={existingPromptNames}
                value={promptName}
                onChange={handlePromptNameChange}
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
                      {option === "__NO_OPTIONS__" ? "No existing prompts" : option}
                    </li>
                  );
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    placeholder="Enter prompt name or select existing..."
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
              <TextField
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Enter prompt instructions..."
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
            disabled={isLoading || !promptName.trim() || !instructions.trim() || !modelProvider || !modelName.trim()}
            sx={{ minWidth: 120 }}
          >
            {isLoading ? "Saving..." : "Save Prompt"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default PromptFormModal;
