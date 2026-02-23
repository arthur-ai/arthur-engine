import { Dispatch, SetStateAction, useCallback, useEffect, useRef, useState } from "react";

import { ExperimentExecutionState, PromptAction, PromptPlaygroundState } from "../types";
import { toExperimentPromptConfig } from "../utils/toExperimentPromptConfig";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { PromptExperimentDetail, PromptExperimentSummary } from "@/lib/api-client/api-client";
import { track, EVENT_NAMES } from "@/services/amplitude";

interface UseExperimentExecutionArgs {
  experimentConfig: Partial<PromptExperimentDetail> | null;
  setExperimentRuns: Dispatch<SetStateAction<PromptExperimentSummary[]>>;
  configModeActive: boolean;
  state: PromptPlaygroundState;
  dispatch: Dispatch<PromptAction>;
  notebookId: string | null;
  refetchNotebookHistory: () => void;
}

/**
 * Manages experiment execution: run all/single, polling, status tracking,
 * expand/collapse run details.
 */
export function useExperimentExecution({
  experimentConfig,
  setExperimentRuns,
  configModeActive,
  state,
  dispatch,
  notebookId,
  refetchNotebookHistory,
}: UseExperimentExecutionArgs) {
  const apiClient = useApi();
  const { task } = useTask();

  const [execState, setExecState] = useState<ExperimentExecutionState>({ status: "idle" });
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const isRunningExperiment = execState.status === "starting" || execState.status === "running";
  const runningExperimentId = execState.status === "running" ? execState.experimentId : null;
  const lastCompletedExperimentId = execState.status === "completed" ? execState.experimentId : null;

  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<Map<string, PromptExperimentDetail>>(new Map());

  const refreshExperimentRuns = useCallback(async () => {
    if (notebookId) {
      refetchNotebookHistory();
      return;
    }

    if (!experimentConfig || !task?.id || !apiClient) return;

    try {
      const experimentsListResponse = await apiClient.api.listPromptExperimentsApiV1TasksTaskIdPromptExperimentsGet({
        taskId: task.id,
        page: 0,
        page_size: 100,
      });

      const matchingExperiments = experimentsListResponse.data.data.filter((exp: PromptExperimentSummary) => exp.name === experimentConfig.name);
      setExperimentRuns(matchingExperiments);
    } catch (error) {
      console.error("Failed to refresh experiment runs:", error);
    }
  }, [notebookId, refetchNotebookHistory, experimentConfig, task?.id, apiClient, setExperimentRuns]);

  const pollExperimentStatus = useCallback(
    async (expId: string) => {
      if (!apiClient) return;

      try {
        const response = await apiClient.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(expId);
        const experiment = response.data;

        if (experiment.status !== "completed" && experiment.status !== "failed") {
          return;
        }

        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setExecState({ status: "completed", experimentId: expId });

        await refreshExperimentRuns();

        setExpandedRunId(expId);
        setRunDetails((prev) => new Map(prev).set(expId, experiment));
      } catch (error) {
        console.error("Failed to poll experiment status:", error);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setExecState({ status: "error" });
      }
    },
    [apiClient, refreshExperimentRuns]
  );

  const startPolling = useCallback(
    (expId: string) => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }

      pollingIntervalRef.current = setInterval(() => {
        pollExperimentStatus(expId);
      }, 2000);

      pollExperimentStatus(expId);
    },
    [pollExperimentStatus]
  );

  const handleRunAllWithConfig = useCallback(async () => {
    if (!experimentConfig || !task?.id || !apiClient) {
      console.error("Missing config, task, or API client");
      return;
    }

    if (!experimentConfig.name) {
      console.error("Missing name in experiment config");
      return;
    }

    if (!experimentConfig.dataset_ref) {
      console.error("Missing dataset_ref in experiment config");
      return;
    }

    if (isRunningExperiment) return;

    try {
      setExecState({ status: "starting" });

      const promptConfigs = state.prompts.map((prompt) => toExperimentPromptConfig(prompt));

      const experimentRequest = {
        name: experimentConfig.name!,
        description: experimentConfig.description,
        dataset_ref: {
          id: experimentConfig.dataset_ref.id,
          version: experimentConfig.dataset_ref.version,
        },
        eval_list: (experimentConfig.eval_list || []).map((evalRef) => ({
          name: evalRef.name,
          version: evalRef.version,
          variable_mapping: evalRef.variable_mapping,
        })),
        prompt_configs: promptConfigs,
        prompt_variable_mapping: experimentConfig.prompt_variable_mapping || [],
        dataset_row_filter:
          experimentConfig.dataset_row_filter && experimentConfig.dataset_row_filter.length > 0 ? experimentConfig.dataset_row_filter : undefined,
        notebook_id: notebookId || undefined,
      };

      const response = await apiClient.api.createPromptExperimentApiV1TasksTaskIdPromptExperimentsPost(task.id, experimentRequest);

      const newExperimentId = response.data.id;
      setExecState({ status: "running", experimentId: newExperimentId });

      startPolling(newExperimentId);

      track(EVENT_NAMES.EXPERIMENT_RUN_STARTED, {
        prompt_count: promptConfigs.length,
        dataset_id: experimentConfig.dataset_ref?.id,
        eval_count: experimentConfig.eval_list?.length || 0,
      });
      track(EVENT_NAMES.RUN_ALL_PROMPTS, {
        prompt_count: promptConfigs.length,
        config_mode: true,
      });
    } catch (error) {
      console.error("Failed to create experiment:", error);
      setExecState({ status: "error" });
    }
  }, [experimentConfig, task?.id, apiClient, state.prompts, isRunningExperiment, startPolling, notebookId]);

  const handleRunSingleWithConfig = useCallback(
    async (promptId: string) => {
      if (!experimentConfig || !task?.id || !apiClient) {
        console.error("Missing config, task, or API client");
        return;
      }

      if (!experimentConfig.name) {
        console.error("Missing name in experiment config");
        return;
      }

      if (!experimentConfig.dataset_ref) {
        console.error("Missing dataset_ref in experiment config");
        return;
      }

      if (isRunningExperiment) return;

      const prompt = state.prompts.find((p) => p.id === promptId);
      if (!prompt) {
        console.error("Prompt not found");
        return;
      }

      try {
        setExecState({ status: "starting" });

        const promptConfig = toExperimentPromptConfig(prompt);

        const experimentRequest = {
          name: experimentConfig.name!,
          description: experimentConfig.description,
          dataset_ref: {
            id: experimentConfig.dataset_ref.id,
            version: experimentConfig.dataset_ref.version,
          },
          eval_list: (experimentConfig.eval_list || []).map((evalRef) => ({
            name: evalRef.name,
            version: evalRef.version,
            variable_mapping: evalRef.variable_mapping,
          })),
          prompt_configs: [promptConfig],
          prompt_variable_mapping: experimentConfig.prompt_variable_mapping || [],
          dataset_row_filter:
            experimentConfig.dataset_row_filter && experimentConfig.dataset_row_filter.length > 0 ? experimentConfig.dataset_row_filter : undefined,
          notebook_id: notebookId || undefined,
        };

        const response = await apiClient.api.createPromptExperimentApiV1TasksTaskIdPromptExperimentsPost(task.id, experimentRequest);

        const newExperimentId = response.data.id;
        setExecState({ status: "running", experimentId: newExperimentId });

        startPolling(newExperimentId);

        track(EVENT_NAMES.EXPERIMENT_RUN_STARTED, {
          prompt_count: 1,
          dataset_id: experimentConfig.dataset_ref?.id,
          eval_count: experimentConfig.eval_list?.length || 0,
        });
      } catch (error) {
        console.error("Failed to create experiment:", error);
        setExecState({ status: "error" });
      }
    },
    [experimentConfig, task?.id, apiClient, state.prompts, isRunningExperiment, startPolling, notebookId]
  );

  const handleRunAllPrompts = useCallback(() => {
    if (configModeActive && experimentConfig) {
      handleRunAllWithConfig();
      return;
    }

    const nonRunningPrompts = state.prompts.filter((prompt) => !prompt.running);
    const promptCount = nonRunningPrompts.length;

    track(EVENT_NAMES.RUN_ALL_PROMPTS, {
      prompt_count: promptCount,
      config_mode: false,
    });

    state.prompts.forEach((prompt) => {
      if (!prompt.running) {
        dispatch({ type: "runPrompt", payload: { promptId: prompt.id } });
      }
    });
  }, [configModeActive, experimentConfig, handleRunAllWithConfig, state.prompts, dispatch]);

  const handleExpandRun = useCallback(
    async (runId: string) => {
      if (expandedRunId === runId) {
        setExpandedRunId(null);
        return;
      }

      setExpandedRunId(runId);

      if (!runDetails.has(runId) && apiClient) {
        try {
          const response = await apiClient.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(runId);
          setRunDetails((prev) => new Map(prev).set(runId, response.data));
        } catch (error) {
          console.error("Failed to fetch run details:", error);
        }
      }
    },
    [expandedRunId, runDetails, apiClient]
  );

  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  return {
    isRunningExperiment,
    runningExperimentId,
    lastCompletedExperimentId,
    expandedRunId,
    runDetails,
    handleRunAllPrompts,
    handleRunSingleWithConfig,
    handleExpandRun,
  };
}
