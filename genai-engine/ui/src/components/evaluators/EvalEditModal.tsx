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

import NunjucksHighlightedTextField from "./MustacheHighlightedTextField";

import { useApi } from "@/hooks/useApi";
import type { CreateEvalRequest, ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";

interface EvalEditModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CreateEvalRequest) => Promise<void>;
  isLoading?: boolean;
  evalName: string;
  initialInstructions: string;
  initialModelProvider: ModelProvider;
  initialModelName: string;
}

const EvalEditModal = ({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  evalName,
  initialInstructions,
  initialModelProvider,
  initialModelName,
}: EvalEditModalProps) => {
  const apiClient = useApi();
  const [instructions, setInstructions] = useState(initialInstructions);
  const [modelProvider, setModelProvider] = useState<ModelProvider | "">(initialModelProvider);
  const [modelName, setModelName] = useState(initialModelName);
  const [error, setError] = useState<string | null>(null);
  const [enabledProviders, setEnabledProviders] = useState<ModelProvider[]>([]);
  const [availableModels, setAvailableModels] = useState<Map<ModelProvider, string[]>>(new Map());
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);

  // Reset form when initial values change
  useEffect(() => {
    setInstructions(initialInstructions);
    setModelProvider(initialModelProvider);
    setModelName(initialModelName);
  }, [initialInstructions, initialModelProvider, initialModelName]);

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

  // Fetch providers when modal opens
  useEffect(() => {
    if (open) {
      // Reset refs when modal opens to allow fresh data fetch
      hasFetchedProviders.current = false;
      hasFetchedAvailableModels.current = false;
      fetchProviders();
    }
  }, [open, fetchProviders]);

  // Fetch available models when providers are loaded
  useEffect(() => {
    if (enabledProviders.length > 0) {
      fetchAvailableModels();
    }
  }, [enabledProviders, fetchAvailableModels]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

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

      await onSubmit(data);

      // Reset form on success
      setInstructions(initialInstructions);
      setModelProvider(initialModelProvider);
      setModelName(initialModelName);
      setError(null);
    } catch (err) {
      console.error("Failed to update eval:", err);

      // Extract error message from API response
      let errorMessage = "Failed to update eval. Please try again.";

      if (err && typeof err === "object") {
        if ("response" in err && err.response && typeof err.response === "object" && "data" in err.response) {
          const responseData = err.response.data;
          if (responseData && typeof responseData === "object" && "detail" in responseData) {
            errorMessage = String(responseData.detail);
          }
        } else if ("message" in err && typeof err.message === "string") {
          errorMessage = err.message;
        }
      } else if (typeof err === "string") {
        errorMessage = err;
      }

      setError(errorMessage);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setInstructions(initialInstructions);
      setModelProvider(initialModelProvider);
      setModelName(initialModelName);
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

  const providerDisabled = enabledProviders.length === 0;
  const modelDisabled = modelProvider === "";
  const tooltipTitle = providerDisabled ? "No providers available. Please configure at least one provider." : "";
  const availableModelsForProvider = useMemo(() => availableModels.get(modelProvider as ModelProvider) || [], [availableModels, modelProvider]);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Edit Eval</DialogTitle>
      <form onSubmit={handleSubmit}>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}>
            <FormControl fullWidth>
              <FormLabel>
                <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                  Eval Name
                </Typography>
              </FormLabel>
              <TextField
                value={evalName}
                disabled
                size="small"
                sx={{
                  "& .MuiInputBase-input.Mui-disabled": {
                    WebkitTextFillColor: "rgba(0, 0, 0, 0.6)",
                  },
                }}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                Eval name cannot be changed. Saving will create a new version.
              </Typography>
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
            disabled={isLoading || !instructions.trim() || !modelProvider || !modelName.trim()}
            sx={{ minWidth: 120 }}
          >
            {isLoading ? "Saving..." : "Save Changes"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EvalEditModal;
