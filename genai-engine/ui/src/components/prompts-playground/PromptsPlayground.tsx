import AddIcon from "@mui/icons-material/Add";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Drawer from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import React, { useCallback, useReducer, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";

import PromptComponent from "./prompts/PromptComponent";
import { PromptProvider } from "./PromptsPlaygroundContext";
import { promptsReducer, initialState } from "./reducer";
import { spanToPrompt } from "./utils";
import VariableInputs from "./VariableInputs";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);
  const [searchParams] = useSearchParams();
  const hasFetchedPrompts = useRef(false);
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedSpan = useRef(false);

  const apiClient = useApi();
  const { task } = useTask();
  const taskId = task?.id;
  const spanId = searchParams.get("spanId");

  const fetchPrompts = useCallback(async () => {
    if (hasFetchedPrompts.current) {
      return;
    }

    if (!apiClient || !taskId) {
      console.error("No api client or task id");
      return;
    }

    hasFetchedPrompts.current = true;
    try {
      const response = await apiClient.api.getAllAgenticPromptsApiV1TasksTaskIdPromptsGet({
        taskId,
      });

      dispatch({
        type: "updateBackendPrompts",
        payload: { prompts: response.data.prompt_metadata },
      });
    } catch (error) {
      console.error("Failed to fetch prompt metadata:", error);
    }
  }, [apiClient, taskId]);

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
        const response = await apiClient.api.getModelProvidersApiV1ModelProvidersProviderAvailableModelsGet(provider as ModelProvider);
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
      const spanPrompt = spanToPrompt(spanData);

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
    fetchPrompts();
    fetchProviders();
    if (spanId) {
      fetchSpanData();
    }
  }, [fetchPrompts, fetchProviders, fetchSpanData, spanId]);

  useEffect(() => {
    if (state.enabledProviders.length > 0) {
      fetchAvailableModels();
    }
  }, [state.enabledProviders, fetchAvailableModels]);

  const handleAddPrompt = () => {
    dispatch({ type: "addPrompt" });
  };

  const handleRunAllPrompts = () => {
    state.prompts.forEach((prompt) => {
      if (!prompt.running) {
        // Only run prompts that are not already running
        dispatch({ type: "runPrompt", payload: { promptId: prompt.id } });
      }
    });
  };

  const drawerWidth = 350;
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

  return (
    <PromptProvider state={state} dispatch={dispatch}>
      <Box className="flex h-full bg-gray-300" sx={{ position: "relative" }}>
        <Drawer
          variant="permanent"
          anchor="left"
          sx={{
            zIndex: 1000,
            backgroundColor: "red",
            width: drawerWidth,
            flexShrink: 0,
            position: "absolute",
            top: 0,
            left: 0,
            height: "100%",
            "& .MuiDrawer-paper": {
              width: drawerWidth,
              boxSizing: "border-box",
              position: "absolute",
              top: 0,
              left: 0,
              height: "100%",
              borderRight: "1px solid",
              borderColor: "divider",
            },
          }}
        >
          <Container component="div" maxWidth={false} disableGutters className="p-2 bg-gray-300 flex-shrink-0">
            <Stack direction="row" justifyContent="flex-end" alignItems="center" spacing={2}>
              <Button variant="contained" size="small" onClick={handleAddPrompt} startIcon={<AddIcon />}>
                Add Prompt
              </Button>
              <Button variant="contained" size="small" onClick={handleRunAllPrompts} startIcon={<PlayArrowIcon />}>
                Run All Prompts
              </Button>
            </Stack>
          </Container>
          <VariableInputs />
        </Drawer>
        <Box
          component="main"
          className="flex-1 flex flex-col"
          sx={{
            marginLeft: `${drawerWidth}px`,
            width: `calc(100% - ${drawerWidth}px)`,
          }}
        >
          <Box ref={scrollContainerRef} className="flex-1 overflow-x-auto overflow-y-hidden p-1">
            <Stack direction="row" spacing={1} sx={{ minWidth: "max-content", height: "100%" }}>
              {state.prompts.map((prompt) => (
                <Box
                  key={prompt.id}
                  className="flex-1 h-full"
                  sx={{
                    minWidth: 750,
                    flexShrink: 0,
                  }}
                >
                  <PromptComponent prompt={prompt} />
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
