import AddIcon from "@mui/icons-material/Add";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import CodeIcon from "@mui/icons-material/Code";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import React, { useCallback, useReducer, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useFetchBackendPrompts } from "./hooks/useFetchBackendPrompts";
import PromptComponent from "./prompts/PromptComponent";
import { PromptProvider } from "./PromptsPlaygroundContext";
import { promptsReducer, initialState } from "./reducer";
import apiToFrontendPrompt from "./utils/apiToFrontendPrompt";

import { useApi } from "@/hooks/useApi";
import { ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [searchParams] = useSearchParams();
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedSpan = useRef(false);
  const fetchPrompts = useFetchBackendPrompts();

  const apiClient = useApi();
  const spanId = searchParams.get("spanId");

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
    state.prompts.forEach((prompt) => {
      if (!prompt.running) {
        // Only run prompts that are not already running
        dispatch({ type: "runPrompt", payload: { promptId: prompt.id } });
      }
    });
  };

  const drawerWidth = drawerOpen ? 210 : 64;
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
      {/* <button onClick={() => setDrawerOpen(!drawerOpen)}>Toggle Drawer</button> */}
      <Box className="flex h-full bg-gray-300" sx={{ position: "relative" }}>
        <div>
          <Box sx={{ width: `${drawerWidth}px`, height: "100%", backgroundColor: "white" }}>
            <Collapse in={drawerOpen} collapsedSize={64}>
              <Stack justifyContent="flex-end" alignItems="center" spacing={2} sx={{ pt: 2 }}>
                <IconButton onClick={() => setDrawerOpen(!drawerOpen)} sx={{ height: 32 }}>
                  <ChevronRightIcon />
                </IconButton>
                <Divider />
                <IconButton onClick={handleAddPrompt} color="primary" sx={{ height: 32 }}>
                  <AddIcon />
                </IconButton>
                <IconButton onClick={handleRunAllPrompts} color="primary" sx={{ height: 32 }}>
                  <PlayArrowIcon />
                </IconButton>
                <IconButton onClick={() => {}} color="primary" sx={{ height: 32 }}>
                  <CodeIcon />
                </IconButton>
              </Stack>
              <Stack justifyContent="flex-end" spacing={2} sx={{ pt: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "flex-end", width: "100%" }}>
                  <IconButton onClick={() => setDrawerOpen(!drawerOpen)} sx={{ height: 32 }}>
                    <ChevronLeftIcon />
                  </IconButton>
                </Box>
                <Divider sx={{ margin: 0 }} />
                <Button variant="contained" sx={{ height: 32, width: "100%" }} onClick={handleAddPrompt} startIcon={<AddIcon />}>
                  Add Prompt
                </Button>
                <Button variant="contained" sx={{ height: 32, width: "100%" }} onClick={handleRunAllPrompts} startIcon={<PlayArrowIcon />}>
                  Run All Prompts
                </Button>
                <Button variant="contained" sx={{ height: 32, width: "100%" }} onClick={() => {}}>
                  &#123;&#123;&nbsp;&#125;&#125;&nbsp;Variables
                </Button>
              </Stack>
            </Collapse>
          </Box>
        </div>
        <Box
          component="main"
          className="flex-1 flex flex-col"
          sx={
            {
              // marginLeft: `${drawerWidth}px`,
              // width: `calc(100% - ${drawerWidth}px)`,
            }
          }
        >
          <Box ref={scrollContainerRef} className="flex-1 overflow-x-auto overflow-y-auto p-1">
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

{
  /* <Stack justifyContent="flex-end" alignItems="center" spacing={2} sx={{ pt: 2 }}>
<IconButton onClick={() => setDrawerOpen(!drawerOpen)} sx={{ height: 32 }}>
  <ChevronRightIcon />
</IconButton>
<Divider />
<IconButton onClick={handleAddPrompt} color="primary" sx={{ height: 32 }}>
  <AddIcon />
</IconButton>
<IconButton onClick={handleRunAllPrompts} color="primary" sx={{ height: 32 }}>
  <PlayArrowIcon />
</IconButton>
<IconButton onClick={() => {}} color="primary" sx={{ height: 32 }}>
  <CodeIcon />
</IconButton>
</Stack>

<Stack justifyContent="flex-end" spacing={2} sx={{ pt: 2 }}>
<Box sx={{ display: "flex", justifyContent: "flex-end", width: "100%" }}>
  <IconButton onClick={() => setDrawerOpen(!drawerOpen)} sx={{ height: 32 }}>
    <ChevronLeftIcon />
  </IconButton>
</Box>
<Divider sx={{ margin: 0 }} />
<Button variant="contained" sx={{ height: 32, width: "100%" }} onClick={handleAddPrompt} startIcon={<AddIcon />}>
  Add Prompt
</Button>
<Button variant="contained" sx={{ height: 32, width: "100%" }} onClick={handleRunAllPrompts} startIcon={<PlayArrowIcon />}>
  Run All Prompts
</Button>
<Button variant="contained" sx={{ height: 32, width: "100%" }} onClick={() => {}}>
  &#123;&#123;&nbsp;&#125;&#125;&nbsp;Variables
</Button>
</Stack> */
}
