import AddIcon from "@mui/icons-material/Add";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import TuneIcon from "@mui/icons-material/Tune";
import Badge from "@mui/material/Badge";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import Stack from "@mui/material/Stack";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useReducer, useEffect, useRef, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { useFetchBackendPrompts } from "./hooks/useFetchBackendPrompts";
import PromptComponent from "./prompts/PromptComponent";
import { PromptProvider } from "./PromptsPlaygroundContext";
import { promptsReducer, initialState } from "./reducer";
import apiToFrontendPrompt from "./utils/apiToFrontendPrompt";
import toFrontendPrompt from "./utils/toFrontendPrompt";
import { toExperimentPromptConfig } from "./utils/toExperimentPromptConfig";
import VariableInputs from "./VariableInputs";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { ModelProvider, ModelProviderResponse } from "@/lib/api-client/api-client";
import { useNavigate } from "react-router-dom";
import { track, EVENT_NAMES } from "@/services/amplitude";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [variablesDrawerOpen, setVariablesDrawerOpen] = useState(false);
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false);
  const variablesButtonRef = useRef<HTMLButtonElement>(null);
  const hasFetchedProviders = useRef(false);
  const hasFetchedAvailableModels = useRef(false);
  const hasFetchedSpan = useRef(false);
  const hasFetchedConfig = useRef(false);
  const fetchPrompts = useFetchBackendPrompts();

  const apiClient = useApi();
  const { task } = useTask();
  const spanId = searchParams.get("spanId");
  const experimentId = searchParams.get("experimentId");
  const promptName = searchParams.get("promptName");
  const promptVersion = searchParams.get("promptVersion");

  // Track if playground is opened with config from "Open in Notebook"
  const isConfigMode = !!(experimentId && promptName && promptVersion);
  const [configModeActive, setConfigModeActive] = useState(isConfigMode);
  const [experimentConfig, setExperimentConfig] = useState<any>(null);
  const [experimentRuns, setExperimentRuns] = useState<any[]>([]);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<Map<string, any>>(new Map());

  // Track the currently running experiment for this session
  const [runningExperimentId, setRunningExperimentId] = useState<string | null>(null);
  const [isRunningExperiment, setIsRunningExperiment] = useState(false);
  const [lastCompletedExperimentId, setLastCompletedExperimentId] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

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

  /**
   * Fetch experiment config and populate the first prompt with the selected prompt version
   * Triggered when URL has experimentId, promptName, and promptVersion parameters
   */
  const fetchExperimentConfig = useCallback(async () => {
    if (hasFetchedConfig.current || !experimentId || !promptName || !promptVersion || !apiClient || !task?.id) {
      return;
    }

    hasFetchedConfig.current = true;

    try {
      // Fetch the experiment details to get config info
      const experimentResponse = await apiClient.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(experimentId);
      const configData = experimentResponse.data;
      setExperimentConfig(configData);

      // Fetch all experiments with the same name to show runs history
      const experimentsListResponse = await apiClient.api.listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet({
        taskId: task.id,
        page: 0,
        pageSize: 100, // Fetch up to 100 experiments
      });

      // Filter experiments with the same name as the current config
      const matchingExperiments = experimentsListResponse.data.data.filter(
        (exp: any) => exp.name === configData.name
      );
      setExperimentRuns(matchingExperiments);

      // Fetch the specific prompt version using the correct API endpoint
      const promptResponse = await apiClient.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
        promptName,
        promptVersion,
        task.id
      );

      // Convert backend prompt to frontend format
      const frontendPrompt = toFrontendPrompt(promptResponse.data);

      if (state.prompts.length > 0) {
        dispatch({
          type: "updatePrompt",
          payload: { promptId: state.prompts[0].id, prompt: frontendPrompt },
        });
      } else {
        dispatch({
          type: "hydratePrompt",
          payload: { promptData: frontendPrompt },
        });
      }

      // Initialize variable values from the experiment config
      // The variable mappings tell us which variables exist in the prompt
      if (configData.prompt_variable_mapping && configData.prompt_variable_mapping.length > 0) {
        configData.prompt_variable_mapping.forEach((mapping: any) => {
          // Initialize each variable with empty string
          // User will need to fill these in or they'll be replaced by dataset values when running
          dispatch({
            type: "updateKeywordValue",
            payload: {
              keyword: mapping.variable_name,
              value: "",
            },
          });
        });
      }
    } catch (error) {
      console.error("Failed to fetch experiment config:", error);
    }
  }, [experimentId, promptName, promptVersion, apiClient, task, state.prompts]);

  useEffect(() => {
    if (isConfigMode) {
      fetchExperimentConfig();
    }
  }, [fetchExperimentConfig, isConfigMode]);

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

  /**
   * Refresh experiment runs list
   */
  const refreshExperimentRuns = useCallback(async () => {
    if (!experimentConfig || !task?.id || !apiClient) return;

    try {
      const experimentsListResponse = await apiClient.api.listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet({
        taskId: task.id,
        page: 0,
        page_size: 100,
      });

      const matchingExperiments = experimentsListResponse.data.data.filter(
        (exp: any) => exp.name === experimentConfig.name
      );
      setExperimentRuns(matchingExperiments);
    } catch (error) {
      console.error("Failed to refresh experiment runs:", error);
    }
  }, [experimentConfig, task?.id, apiClient]);

  /**
   * Poll experiment status until completion
   */
  const pollExperimentStatus = useCallback(
    async (expId: string) => {
      if (!apiClient) return;

      try {
        const response = await apiClient.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(expId);
        const experiment = response.data;

        // Check if experiment is still running, queued, or evaluating
        // Keep polling while status is not completed or failed
        if (experiment.status === "running" || experiment.status === "queued" || experiment.status === "evaluating") {
          // Continue polling
          return;
        }

        // Experiment completed or failed - stop polling
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setIsRunningExperiment(false);
        // Keep the experiment ID so results persist, but store in lastCompleted
        setLastCompletedExperimentId(expId);
        setRunningExperimentId(null);

        // Refresh the runs list to show the completed experiment
        await refreshExperimentRuns();

        // Auto-expand the completed run details
        setExpandedRunId(expId);
        setRunDetails((prev) => new Map(prev).set(expId, experiment));
      } catch (error) {
        console.error("Failed to poll experiment status:", error);
        // Stop polling on error
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setIsRunningExperiment(false);
        setRunningExperimentId(null);
      }
    },
    [apiClient, refreshExperimentRuns]
  );

  /**
   * Start polling for experiment completion
   */
  const startPolling = useCallback(
    (expId: string) => {
      // Clear any existing polling
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }

      // Poll every 2 seconds
      pollingIntervalRef.current = setInterval(() => {
        pollExperimentStatus(expId);
      }, 2000);

      // Also do an immediate poll
      pollExperimentStatus(expId);
    },
    [pollExperimentStatus]
  );

  /**
   * Run experiment with all prompts in config mode
   */
  const handleRunAllWithConfig = useCallback(async () => {
    if (!experimentConfig || !task?.id || !apiClient) {
      console.error("Missing config, task, or API client");
      return;
    }

    if (isRunningExperiment) {
      console.warn("An experiment is already running");
      return;
    }

    try {
      setIsRunningExperiment(true);

      // Convert all playground prompts to experiment prompt configs
      const promptConfigs = state.prompts.map((prompt) => toExperimentPromptConfig(prompt));

      // Create experiment request using the same config as the original
      // Use the original prompt_variable_mapping from experimentConfig
      const experimentRequest = {
        name: experimentConfig.name,
        description: experimentConfig.description,
        dataset_ref: experimentConfig.dataset_ref,
        eval_list: experimentConfig.eval_list,
        prompt_configs: promptConfigs,
        prompt_variable_mapping: experimentConfig.prompt_variable_mapping || [],
      };

      // Create and run the experiment
      const response = await apiClient.api.createPromptExperimentApiV1TasksTaskIdPromptExperimentsPost(
        task.id,
        experimentRequest
      );

      const newExperimentId = response.data.id;
      setRunningExperimentId(newExperimentId);

      // Start polling for results
      startPolling(newExperimentId);

      // Track the event
      track(EVENT_NAMES.RUN_ALL_PROMPTS, {
        prompt_count: promptConfigs.length,
        config_mode: true,
      });
    } catch (error) {
      console.error("Failed to create experiment:", error);
      setIsRunningExperiment(false);
      setRunningExperimentId(null);
    }
  }, [experimentConfig, task?.id, apiClient, state.prompts, isRunningExperiment, startPolling]);

  /**
   * Run experiment with a single prompt in config mode
   */
  const handleRunSingleWithConfig = useCallback(async (promptId: string) => {
    if (!experimentConfig || !task?.id || !apiClient) {
      console.error("Missing config, task, or API client");
      return;
    }

    if (isRunningExperiment) {
      console.warn("An experiment is already running");
      return;
    }

    const prompt = state.prompts.find((p) => p.id === promptId);
    if (!prompt) {
      console.error("Prompt not found");
      return;
    }

    try {
      setIsRunningExperiment(true);

      // Convert the single prompt to experiment prompt config
      const promptConfig = toExperimentPromptConfig(prompt);

      // Create experiment request with just this prompt
      const experimentRequest = {
        name: experimentConfig.name,
        description: experimentConfig.description,
        dataset_ref: experimentConfig.dataset_ref,
        eval_list: experimentConfig.eval_list,
        prompt_configs: [promptConfig],
        prompt_variable_mapping: experimentConfig.prompt_variable_mapping || [],
      };

      // Create and run the experiment
      const response = await apiClient.api.createPromptExperimentApiV1TasksTaskIdPromptExperimentsPost(
        task.id,
        experimentRequest
      );

      const newExperimentId = response.data.id;
      setRunningExperimentId(newExperimentId);

      // Start polling for results
      startPolling(newExperimentId);
    } catch (error) {
      console.error("Failed to create experiment:", error);
      setIsRunningExperiment(false);
      setRunningExperimentId(null);
    }
  }, [experimentConfig, task?.id, apiClient, state.prompts, isRunningExperiment, startPolling]);

  const handleRunAllPrompts = () => {
    // If in config mode, run with experiment
    if (configModeActive && experimentConfig) {
      handleRunAllWithConfig();
      return;
    }

    // Otherwise, run in normal playground mode
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

  const toggleConfigDrawer = () => {
    setConfigDrawerOpen((prev) => !prev);
  };

  const handleExpandRun = useCallback(async (runId: string) => {
    if (expandedRunId === runId) {
      setExpandedRunId(null);
      return;
    }

    setExpandedRunId(runId);

    // Fetch details if not already cached
    if (!runDetails.has(runId) && apiClient) {
      try {
        const response = await apiClient.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(runId);
        setRunDetails((prev) => new Map(prev).set(runId, response.data));
      } catch (error) {
        console.error("Failed to fetch run details:", error);
      }
    }
  }, [expandedRunId, runDetails, apiClient]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Count blank variables
  // In config mode, only count variables that are NOT mapped to dataset columns
  const blankVariablesCount = useMemo(() => {
    if (experimentConfig?.prompt_variable_mapping) {
      // Build a set of mapped variable names
      const mappedVariables = new Set<string>();
      experimentConfig.prompt_variable_mapping.forEach((mapping: any) => {
        mappedVariables.add(mapping.variable_name);
      });

      // Only count unmapped variables that are blank
      let count = 0;
      state.keywords.forEach((value, key) => {
        const isMapped = mappedVariables.has(key);
        const isEmpty = !value || value.trim() === "";
        if (!isMapped && isEmpty) {
          count++;
        }
      });
      return count;
    }

    // Normal mode: count all blank variables
    let count = 0;
    state.keywords.forEach((value) => {
      if (!value || value.trim() === "") {
        count++;
      }
    });
    return count;
  }, [state.keywords, experimentConfig]);

  // Check if all prompts have model configuration
  const allPromptsHaveModelConfig = useMemo(() => {
    return state.prompts.every((prompt) => prompt.modelProvider !== "" && prompt.modelName !== "");
  }, [state.prompts]);

  // Check what's missing for run all button tooltip
  const runAllDisabledReason = useMemo(() => {
    if (!allPromptsHaveModelConfig) {
      return "All prompts must have a model provider and model selected";
    }
    if (blankVariablesCount > 0) {
      return "Please fill in all variable values before running";
    }
    if (isRunningExperiment) {
      return "An experiment is currently running";
    }
    return null;
  }, [allPromptsHaveModelConfig, blankVariablesCount, isRunningExperiment]);

  return (
    <PromptProvider
      state={state}
      dispatch={dispatch}
      experimentConfig={experimentConfig}
      handleRunSingleWithConfig={handleRunSingleWithConfig}
      isRunningExperiment={isRunningExperiment}
      runningExperimentId={runningExperimentId}
      lastCompletedExperimentId={lastCompletedExperimentId}
    >
      <Box className="flex flex-col h-full bg-gray-300" sx={{ position: "relative" }}>
        {/* Config Mode Indicator */}
        {configModeActive && experimentConfig && (
          <Box className="bg-blue-100 border-b border-blue-300 px-4 py-2">
            <Box className="flex items-center justify-between">
              <Box className="flex items-center gap-2">
                <Box className="w-2 h-2 bg-blue-600 rounded-full" />
                <span className="text-sm font-medium text-blue-900">
                  Config Mode: Loaded from experiment "{experimentConfig.name}"
                  {experimentConfig.prompt_configs && experimentConfig.prompt_configs.length > 0 && (
                    <span className="ml-2 text-xs">
                      ({experimentConfig.prompt_configs.length} prompt{experimentConfig.prompt_configs.length > 1 ? 's' : ''})
                    </span>
                  )}
                </span>
              </Box>
            </Box>
          </Box>
        )}

        {/* Header with action buttons */}
        <Container component="div" maxWidth={false} disableGutters className="p-2 mt-1 bg-gray-300 shrink-0">
          <Stack direction="row" justifyContent="flex-end" alignItems="center" spacing={2}>
            {configModeActive && (
              <Button
                variant={configDrawerOpen ? "contained" : "outlined"}
                size="small"
                onClick={toggleConfigDrawer}
                startIcon={<InfoOutlinedIcon />}
              >
                Config
              </Button>
            )}
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
            <Tooltip title={runAllDisabledReason || "Run All Prompts"} arrow>
              <span>
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleRunAllPrompts}
                  startIcon={<PlayArrowIcon />}
                  disabled={!!runAllDisabledReason}
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

        {/* Config Drawer */}
        <Drawer
          anchor="right"
          open={configDrawerOpen}
          onClose={toggleConfigDrawer}
          variant="temporary"
          sx={{
            zIndex: (theme) => theme.zIndex.drawer + 2,
            "& .MuiDrawer-paper": {
              width: 480,
              boxSizing: "border-box",
            },
          }}
        >
          <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
            {/* Drawer Header */}
            <Box sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: 1, borderColor: "divider" }}>
              <Typography variant="h6">Experiment Configuration</Typography>
              <IconButton onClick={toggleConfigDrawer} size="small">
                <ChevronLeftIcon />
              </IconButton>
            </Box>

            {/* Drawer Content */}
            <Box sx={{ flex: 1, overflowY: "auto", p: 3 }}>
              {experimentConfig ? (
                <Stack spacing={3}>
                  {/* Experiment Name Section */}
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: "text.secondary" }}>
                      EXPERIMENT
                    </Typography>
                    <Box sx={{ pl: 2, display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {experimentConfig.name}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={() => navigate(`/tasks/${task.id}/prompt-experiments/${experimentConfig.id}`)}
                        sx={{
                          padding: 0.5,
                          color: "#9ca3af",
                          "&:hover": {
                            color: "#6b7280",
                            backgroundColor: "rgba(0, 0, 0, 0.04)",
                          },
                        }}
                      >
                        <OpenInNewIcon sx={{ fontSize: "0.875rem" }} />
                      </IconButton>
                    </Box>
                  </Box>

                  <Divider />

                  {/* Dataset Section */}
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1, color: "text.secondary" }}>
                      DATASET
                    </Typography>
                    <Box sx={{ pl: 2 }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {experimentConfig.dataset_ref?.name?.trim() || experimentConfig.dataset_ref?.id || "Unknown"}
                        </Typography>
                        {experimentConfig.dataset_ref?.id && (
                          <IconButton
                            size="small"
                            onClick={() => navigate(`/tasks/${task.id}/datasets/${experimentConfig.dataset_ref.id}`)}
                            sx={{
                              padding: 0.5,
                              color: "#9ca3af",
                              "&:hover": {
                                color: "#6b7280",
                                backgroundColor: "rgba(0, 0, 0, 0.04)",
                              },
                            }}
                          >
                            <OpenInNewIcon sx={{ fontSize: "0.875rem" }} />
                          </IconButton>
                        )}
                      </Box>
                      {experimentConfig.dataset_ref?.version && (
                        <Typography variant="body2" sx={{ color: "text.secondary", fontSize: "0.813rem" }}>
                          Version {experimentConfig.dataset_ref.version}
                        </Typography>
                      )}
                    </Box>
                  </Box>

                  <Divider />

                  {/* Prompt Variable Mappings Section */}
                  {experimentConfig.prompt_ref?.variable_mapping && experimentConfig.prompt_ref.variable_mapping.length > 0 && (
                    <>
                      <Box>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: "text.secondary" }}>
                          PROMPT VARIABLE MAPPINGS
                        </Typography>
                        <Stack spacing={1}>
                          {experimentConfig.prompt_ref.variable_mapping.map((mapping: any, idx: number) => (
                            <Box
                              key={idx}
                              sx={{
                                backgroundColor: "#e3f2fd",
                                borderLeft: "3px solid #2196f3",
                                px: 1.5,
                                py: 1,
                                borderRadius: 0.5,
                              }}
                            >
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: "0.813rem",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                <Box component="span" sx={{ fontWeight: 600 }}>
                                  {mapping.variable_name}
                                </Box>
                                {" → Dataset column: "}
                                <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "#1976d2" }}>
                                  {mapping.source?.dataset_column?.name}
                                </Box>
                              </Typography>
                            </Box>
                          ))}
                        </Stack>
                      </Box>
                      <Divider />
                    </>
                  )}

                  {/* Eval Variable Mappings Section */}
                  {experimentConfig.eval_list && experimentConfig.eval_list.length > 0 && (
                    <>
                      <Box>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: "text.secondary" }}>
                          EVAL VARIABLE MAPPINGS
                        </Typography>
                        <Stack spacing={2}>
                          {experimentConfig.eval_list.map((evalRef: any, evalIdx: number) => (
                            <Box key={evalIdx}>
                              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
                                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.813rem" }}>
                                  {evalRef.name} <Box component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>(v{evalRef.version})</Box>
                                </Typography>
                                <IconButton
                                  size="small"
                                  onClick={() => navigate(`/tasks/${task.id}/evaluators/${encodeURIComponent(evalRef.name)}`)}
                                  sx={{
                                    padding: 0.25,
                                    color: "#9ca3af",
                                    "&:hover": {
                                      color: "#6b7280",
                                      backgroundColor: "rgba(0, 0, 0, 0.04)",
                                    },
                                  }}
                                >
                                  <OpenInNewIcon sx={{ fontSize: "0.75rem" }} />
                                </IconButton>
                              </Box>
                              <Stack spacing={1}>
                                {evalRef.variable_mapping?.map((mapping: any, mapIdx: number) => {
                                  const isDatasetColumn = mapping.source?.type === "dataset_column";
                                  return (
                                    <Box
                                      key={mapIdx}
                                      sx={{
                                        backgroundColor: isDatasetColumn ? "#e3f2fd" : "#fff3e0",
                                        borderLeft: isDatasetColumn ? "3px solid #2196f3" : "3px solid #ff9800",
                                        px: 1.5,
                                        py: 1,
                                        borderRadius: 0.5,
                                      }}
                                    >
                                      <Typography
                                        variant="body2"
                                        sx={{
                                          fontSize: "0.813rem",
                                          overflow: "hidden",
                                          textOverflow: "ellipsis",
                                          whiteSpace: "nowrap",
                                        }}
                                      >
                                        <Box component="span" sx={{ fontWeight: 600 }}>
                                          {mapping.variable_name}
                                        </Box>
                                        {" → "}
                                        {isDatasetColumn ? (
                                          <>
                                            Dataset column: <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "#1976d2" }}>{mapping.source?.dataset_column?.name}</Box>
                                          </>
                                        ) : (
                                          <>
                                            Experiment output
                                            {mapping.source?.experiment_output?.json_path && (
                                              <>
                                                {" "}(path: <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "#f57c00" }}>{mapping.source.experiment_output.json_path}</Box>)
                                              </>
                                            )}
                                          </>
                                        )}
                                      </Typography>
                                    </Box>
                                  );
                                })}
                              </Stack>
                            </Box>
                          ))}
                        </Stack>
                      </Box>
                      <Divider />
                    </>
                  )}

                  {/* Experiment Runs Section */}
                  {experimentRuns.length > 0 && (
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: "text.secondary" }}>
                        EXPERIMENT RUNS ({experimentRuns.length})
                      </Typography>
                      <Stack spacing={1}>
                        {experimentRuns.map((run: any, idx: number) => {
                          const completionRate = run.total_rows > 0 ? (run.completed_rows / run.total_rows) * 100 : 0;
                          const isCompleted = run.status === "completed";
                          const isFailed = run.status === "failed";
                          const isRunning = run.status === "running";
                          const isExpanded = expandedRunId === run.id;
                          const details = runDetails.get(run.id);

                          return (
                            <Box
                              key={idx}
                              sx={{
                                border: "1px solid",
                                borderColor: "divider",
                                borderRadius: 1,
                                overflow: "hidden",
                                backgroundColor: isCompleted ? "#f1f8f4" : isFailed ? "#fef3f2" : "background.paper",
                              }}
                            >
                              <Box
                                onClick={() => handleExpandRun(run.id)}
                                sx={{
                                  px: 1.5,
                                  py: 1,
                                  cursor: "pointer",
                                  "&:hover": { backgroundColor: "action.hover" },
                                }}
                              >
                                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.5 }}>
                                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                                    <ChevronRightIcon
                                      sx={{
                                        fontSize: "1rem",
                                        transform: isExpanded ? "rotate(90deg)" : "rotate(0deg)",
                                        transition: "transform 0.2s",
                                      }}
                                    />
                                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.813rem" }}>
                                      {new Date(run.created_at).toLocaleString()}
                                    </Typography>
                                  </Box>
                                  <Box
                                    component="span"
                                    sx={{
                                      fontSize: "0.688rem",
                                      px: 0.75,
                                      py: 0.25,
                                      borderRadius: 0.5,
                                      backgroundColor: isCompleted ? "#10b981" : isFailed ? "#ef4444" : isRunning ? "#f59e0b" : "#6b7280",
                                      color: "white",
                                      fontWeight: 600,
                                      textTransform: "uppercase",
                                    }}
                                  >
                                    {run.status}
                                  </Box>
                                </Box>
                                <Typography variant="body2" sx={{ fontSize: "0.75rem", color: "text.secondary" }}>
                                  {run.completed_rows}/{run.total_rows} completed • {run.failed_rows} failed • {completionRate.toFixed(1)}% done
                                </Typography>
                                {run.total_cost && (
                                  <Typography variant="body2" sx={{ fontSize: "0.75rem", color: "text.secondary", mt: 0.25 }}>
                                    Cost: ${run.total_cost}
                                  </Typography>
                                )}
                              </Box>

                              {/* Expanded Details */}
                              {isExpanded && details?.summary_results?.prompt_eval_summaries && (
                                <Box
                                  sx={{
                                    borderTop: "1px solid",
                                    borderColor: "divider",
                                    px: 1.5,
                                    py: 1.5,
                                    backgroundColor: "rgba(0, 0, 0, 0.02)",
                                  }}
                                >
                                  <Stack spacing={1.5}>
                                    {details.summary_results.prompt_eval_summaries.map((promptSummary: any, pIdx: number) => (
                                      <Box key={pIdx}>
                                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.75 }}>
                                          <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.75rem" }}>
                                            {promptSummary.prompt_name} <Box component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>(v{promptSummary.prompt_version})</Box>
                                          </Typography>
                                          <IconButton
                                            size="small"
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              navigate(`/tasks/${task.id}/prompts/${encodeURIComponent(promptSummary.prompt_name)}/versions/${promptSummary.prompt_version}`);
                                            }}
                                            sx={{
                                              padding: 0.25,
                                              color: "#9ca3af",
                                              "&:hover": {
                                                color: "#6b7280",
                                                backgroundColor: "rgba(0, 0, 0, 0.04)",
                                              },
                                            }}
                                          >
                                            <OpenInNewIcon sx={{ fontSize: "0.65rem" }} />
                                          </IconButton>
                                        </Box>
                                        <Stack spacing={0.75}>
                                          {promptSummary.eval_results.map((evalResult: any, eIdx: number) => {
                                            const percentage = evalResult.total_count > 0 ? (evalResult.pass_count / evalResult.total_count) * 100 : 0;
                                            return (
                                              <Box key={eIdx} sx={{ pl: 1 }}>
                                                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.25 }}>
                                                  <Typography variant="caption" sx={{ fontSize: "0.688rem", color: "text.secondary" }}>
                                                    {evalResult.eval_name} (v{evalResult.eval_version})
                                                  </Typography>
                                                  <Typography variant="caption" sx={{ fontSize: "0.688rem", fontWeight: 600 }}>
                                                    {evalResult.pass_count}/{evalResult.total_count} ({percentage.toFixed(0)}%)
                                                  </Typography>
                                                </Box>
                                              </Box>
                                            );
                                          })}
                                        </Stack>
                                      </Box>
                                    ))}
                                  </Stack>
                                </Box>
                              )}
                            </Box>
                          );
                        })}
                      </Stack>
                    </Box>
                  )}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No configuration data available
                </Typography>
              )}
            </Box>
          </Box>
        </Drawer>
      </Box>
    </PromptProvider>
  );
};

export default PromptsPlayground;
