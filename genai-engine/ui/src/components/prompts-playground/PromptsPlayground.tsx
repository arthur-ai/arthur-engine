import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import TuneIcon from "@mui/icons-material/Tune";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import { useCallback, useReducer, useEffect, useRef, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useFetchBackendPrompts } from "./hooks/useFetchBackendPrompts";
import PromptComponent from "./prompts/PromptComponent";
import { PromptProvider } from "./PromptsPlaygroundContext";
import { promptsReducer, initialState } from "./reducer";
import apiToFrontendPrompt from "./utils/apiToFrontendPrompt";
import VariableInputs from "./VariableInputs";

import { useApi } from "@/hooks/useApi";
import { ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";
import { track, EVENT_NAMES } from "@/services/amplitude";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);
  const [searchParams] = useSearchParams();
  const [variablesDrawerOpen, setVariablesDrawerOpen] = useState(false);
  const variablesButtonRef = useRef<HTMLButtonElement>(null);
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedSpan = useRef(false);
  const fetchPrompts = useFetchBackendPrompts();

  const apiClient = useApi();
  const spanId = searchParams.get("spanId");

  // Pass false to let each prompt determine its own icon-only mode based on container width
  // This enables true container query behavior - each prompt measures its own width
  const useIconOnlyMode = false;

  const fetchProviders = useCallback(async () => {
    if (hasFetchedProviders.current) {
      return;
    }

    if (!apiClient) {
      console.error("No api client");
      return;
    }

    hasFetchedProviders.current = true;
    const response = await apiClient.api.getModelProvidersApiV1ModelProvidersGet();

    const { data } = response;
    const providers = data.providers
      .filter((provider: ModelProviderResponse) => provider.enabled)
      .map((provider: ModelProviderResponse) => provider.provider);

    dispatch({
      type: "updateProviders",
      payload: { providers },
    });
  }, [apiClient]);

  const fetchAvailableModels = useCallback(async () => {
    if (hasFetchedAvailableModels.current || !apiClient || state.enabledProviders.length === 0) {
      return;
    }

    hasFetchedAvailableModels.current = true;

    // Fetch models for all enabled providers in parallel
    const modelPromises = state.enabledProviders.map(async (provider) => {
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

    // Single dispatch with the complete Map
    dispatch({
      type: "updateAvailableModels",
      payload: { availableModels: newAvailableModels },
    });
  }, [apiClient, state.enabledProviders]);

  /**
   * Fetch span data and update the first empty prompt
   * Triggered if URL has a spanId parameter
   */
  const fetchSpanData = useCallback(async () => {
    if (hasFetchedSpan.current || !spanId || !apiClient) {
      return;
    }

    hasFetchedSpan.current = true;

    try {
      const response = await apiClient.api.getSpanByIdApiV1TracesSpansSpanIdGet(spanId);
      const spanData = response.data;
      const spanPrompt = apiToFrontendPrompt(spanData);

      // Update the first empty prompt instead of adding a new one
      if (state.prompts.length > 0) {
        dispatch({
          type: "updatePrompt",
          payload: { promptId: state.prompts[0].id, prompt: spanPrompt },
        });
      } else {
        dispatch({
          type: "hydratePrompt",
          payload: { promptData: spanPrompt },
        });
      }
    } catch (error) {
      console.error("Failed to fetch span data:", error);
    }
  }, [spanId, apiClient, state.prompts]);

  useEffect(() => {
    if (spanId) {
      fetchSpanData();
    }
  }, [fetchSpanData, spanId]);

  // Fetch backend prompts on mount
  useEffect(() => {
    fetchPrompts(dispatch);
  }, [fetchPrompts]);

  // Fetch providers on mount
  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  // If providers exist, fetch available models
  useEffect(() => {
    if (state.enabledProviders.length > 0) {
      fetchAvailableModels();
    }
  }, [state.enabledProviders, fetchAvailableModels]);

  const handleAddPrompt = () => {
    dispatch({ type: "addPrompt" });
  };

  const handleRunAllPrompts = () => {
    // Calculate tracking properties
    const nonRunningPrompts = state.prompts.filter((prompt) => !prompt.running);
    const promptCount = nonRunningPrompts.length;

    // Track the event
    track(EVENT_NAMES.RUN_ALL_PROMPTS, {
      prompt_count: promptCount,
    });

    // Run all non-running prompts
    state.prompts.forEach((prompt) => {
      if (!prompt.running) {
        // Only run prompts that are not already running
        dispatch({ type: "runPrompt", payload: { promptId: prompt.id } });
      }
    });
  };

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      // Only intercept when Shift is held (explicit horizontal scroll intent)
      // This prevents conflicts with vertical scrolling in child elements
      if (e.shiftKey) {
        e.preventDefault();
        // Use deltaX if available (trackpad horizontal scroll), otherwise convert deltaY to horizontal
        container.scrollLeft += e.deltaX || e.deltaY;
      }
      // When Shift is NOT held, allow normal vertical scrolling to pass through to child elements
    };

    // Add event listener with { passive: false } to allow preventDefault
    container.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      container.removeEventListener("wheel", handleWheel);
    };
  }, []);

  const toggleVariablesDrawer = () => {
    setVariablesDrawerOpen((prev) => !prev);
  };

  // Count blank variables
  const blankVariablesCount = useMemo(() => {
    let count = 0;
    state.keywords.forEach((value) => {
      if (!value || value.trim() === "") {
        count++;
      }
    });
    return count;
  }, [state.keywords]);

  return (
    <PromptProvider state={state} dispatch={dispatch}>
      <Box className="flex flex-col h-full bg-gray-300" sx={{ position: "relative" }}>
        {/* Header with action buttons */}
        <Container component="div" maxWidth={false} disableGutters className="p-2 mt-1 bg-gray-300 shrink-0">
          <Stack direction="row" justifyContent="flex-end" alignItems="center" spacing={2}>
            <Box sx={{ position: "relative" }}>
              <Badge badgeContent={blankVariablesCount} color="error" overlap="rectangular">
                <Button
                  ref={variablesButtonRef}
                  variant={variablesDrawerOpen ? "contained" : "outlined"}
                  color={variablesDrawerOpen ? "primary" : "primary"}
                  size="small"
                  onClick={toggleVariablesDrawer}
                  startIcon={<TuneIcon />}
                >
                  Variables
                </Button>
                <Popover
                  open={variablesDrawerOpen}
                  onClose={toggleVariablesDrawer}
                  anchorEl={variablesButtonRef.current}
                  anchorOrigin={{
                    vertical: "bottom",
                    horizontal: "left",
                  }}
                  slotProps={{
                    paper: {
                      sx: { width: "400px", maxHeight: "500px" },
                    },
                  }}
                  sx={{ marginTop: "6px" }}
                >
                  <VariableInputs />
                </Popover>
              </Badge>
            </Box>
            <Button variant="contained" size="small" onClick={handleAddPrompt} startIcon={<AddIcon />}>
              Add Prompt
            </Button>
            <Tooltip title={blankVariablesCount > 0 ? "Please fill in all variable values before running" : "Run All Prompts"} arrow>
              <span>
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleRunAllPrompts}
                  startIcon={<PlayArrowIcon />}
                  disabled={blankVariablesCount > 0}
                >
                  Run All Prompts
                </Button>
              </span>
            </Tooltip>
          </Stack>
        </Container>

        {/* Main content area */}
        <Box component="main" className="flex-1 flex flex-col">
          <Box ref={scrollContainerRef} className="flex-1 overflow-x-auto overflow-y-auto p-1">
            <Stack direction="row" spacing={1} sx={{ height: "100%" }}>
              {state.prompts.map((prompt) => (
                <Box
                  key={prompt.id}
                  className="flex-1 h-full"
                  sx={{
                    minWidth: 400,
                  }}
                >
                  <PromptComponent prompt={prompt} useIconOnlyMode={useIconOnlyMode} />
                </Box>
              ))}
            </Stack>
          </Box>
        </Box>
      </Box>
    </PromptProvider>
  );
};

export default PromptsPlayground;
