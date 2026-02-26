import { Dispatch, MutableRefObject, SetStateAction, useCallback, useState } from "react";

import { PlaygroundInitialData, PromptAction, PromptPlaygroundState } from "../types";
import toFrontendPrompt from "../utils/toFrontendPrompt";

import type { ExperimentFormData } from "@/components/prompt-experiments/CreateExperimentModal";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import type { PromptExperimentDetail, PromptExperimentSummary, SavedPromptConfig } from "@/lib/api-client/api-client";
import { track, EVENT_NAMES } from "@/services/amplitude";

interface UseExperimentConfigArgs {
  initialData: PlaygroundInitialData;
  state: PromptPlaygroundState;
  dispatch: Dispatch<PromptAction>;
  notebookId: string | null;
  hasUnsavedChangesRef: MutableRefObject<boolean>;
  setSaveStatus: Dispatch<SetStateAction<"saved" | "saving" | "unsaved">>;
  refetchNotebookHistory: () => void;
}

/**
 * Manages experiment config: load/create config, overwrite dialog state, and config-mode activation.
 */
export function useExperimentConfig({
  initialData,
  state,
  dispatch,
  notebookId,
  hasUnsavedChangesRef,
  setSaveStatus,
  refetchNotebookHistory,
}: UseExperimentConfigArgs) {
  const apiClient = useApi();
  const { task } = useTask();

  const [configModeActive, setConfigModeActive] = useState(initialData.isConfigMode);
  const [experimentConfig, setExperimentConfig] = useState<Partial<PromptExperimentDetail> | null>(initialData.experimentConfig);
  const [experimentRuns, setExperimentRuns] = useState<PromptExperimentSummary[]>(initialData.experimentRuns);

  // Overwrite dialog state
  const [createExperimentModalOpen, setCreateExperimentModalOpen] = useState(false);
  const [showPromptOverwriteDialog, setShowPromptOverwriteDialog] = useState(false);
  const [pendingConfigForPromptOverwrite, setPendingConfigForPromptOverwrite] = useState<Partial<PromptExperimentDetail> | null>(null);

  const handleLoadConfig = useCallback(
    async (config: Partial<PromptExperimentDetail>, overwritePrompts: boolean) => {
      if (overwritePrompts && config.prompt_configs && config.prompt_configs.length > 0 && apiClient && task?.id) {
        try {
          const prompts = [];
          for (const promptConfig of config.prompt_configs) {
            if (promptConfig.type === "saved") {
              const savedConfig = promptConfig as SavedPromptConfig & { type: "saved" };
              try {
                const promptResponse = await apiClient.api.getAgenticPromptApiV1TasksTaskIdPromptsPromptNameVersionsPromptVersionGet(
                  savedConfig.name,
                  savedConfig.version.toString(),
                  task.id
                );
                const frontendPrompt = toFrontendPrompt(promptResponse.data);
                prompts.push(frontendPrompt);
              } catch (error) {
                console.error(`Failed to fetch saved prompt ${savedConfig.name} v${savedConfig.version}:`, error);
              }
            }
          }

          if (prompts.length > 0) {
            dispatch({
              type: "hydrateNotebookState",
              payload: {
                prompts,
                keywords: new Map<string, string>(),
              },
            });
          }
        } catch (error) {
          console.error("Failed to load prompts from experiment:", error);
        }
      }

      setExperimentConfig(config);
      setConfigModeActive(true);

      hasUnsavedChangesRef.current = true;
      setSaveStatus("unsaved");

      if (notebookId) {
        refetchNotebookHistory();
      }
    },
    [notebookId, apiClient, task?.id, refetchNotebookHistory, dispatch, hasUnsavedChangesRef, setSaveStatus]
  );

  const handleCreateNewConfig = useCallback(() => {
    setCreateExperimentModalOpen(true);
  }, []);

  const handleCreateExperimentSubmit = useCallback(
    async (formData: ExperimentFormData) => {
      const config = {
        name: formData.name,
        description: formData.description,
        dataset_ref: {
          id: formData.datasetId,
          name: formData.datasetName,
          version: formData.datasetVersion as number,
        },
        eval_list: formData.evaluators.map((evalRef) => ({
          name: evalRef.name,
          version: evalRef.version,
          variable_mapping: formData.evalVariableMappings?.find(
            (mapping) => mapping.evalName === evalRef.name && mapping.evalVersion === evalRef.version
          )?.mappings
            ? Object.entries(
                formData.evalVariableMappings.find((mapping) => mapping.evalName === evalRef.name && mapping.evalVersion === evalRef.version)!
                  .mappings
              ).map(([variableName, mapping]) => ({
                variable_name: variableName,
                source:
                  mapping.sourceType === "dataset_column"
                    ? {
                        type: "dataset_column" as const,
                        dataset_column: { name: mapping.datasetColumn! },
                      }
                    : {
                        type: "experiment_output" as const,
                        experiment_output: { json_path: mapping.jsonPath! },
                      },
              }))
            : [],
        })),
        prompt_variable_mapping: formData.promptVariableMappings
          ? Object.entries(formData.promptVariableMappings).map(([variableName, datasetColumn]) => ({
              variable_name: variableName,
              source: {
                type: "dataset_column" as const,
                dataset_column: { name: datasetColumn },
              },
            }))
          : [],
        dataset_row_filter: formData.datasetRowFilter || [],
        prompt_configs: formData.promptVersions.map((pv) => ({
          type: "saved" as const,
          name: pv.promptName,
          version: pv.version,
        })),
      };

      const hasPromptsToLoad = formData.promptVersions.length > 0;
      const hasExistingPrompts = state.prompts.length > 0;

      setCreateExperimentModalOpen(false);

      if (hasPromptsToLoad && hasExistingPrompts) {
        setPendingConfigForPromptOverwrite(config);
        setShowPromptOverwriteDialog(true);
      } else if (hasPromptsToLoad) {
        await handleLoadConfig(config, true);
      } else {
        setExperimentConfig(config);
        setConfigModeActive(true);
        hasUnsavedChangesRef.current = true;
        setSaveStatus("unsaved");

        if (notebookId) {
          refetchNotebookHistory();
        }
      }

      track(EVENT_NAMES.EXPERIMENT_CONFIG_CREATED, {
        dataset_id: config.dataset_ref?.id,
        eval_count: config.eval_list?.length || 0,
        prompt_count: config.prompt_configs?.length || 0,
        has_row_filter: (config.dataset_row_filter?.length || 0) > 0,
      });

      return { id: "config-only" };
    },
    [notebookId, refetchNotebookHistory, state.prompts.length, handleLoadConfig, hasUnsavedChangesRef, setSaveStatus]
  );

  const handlePromptOverwriteConfirm = useCallback(
    async (overwrite: boolean) => {
      if (pendingConfigForPromptOverwrite) {
        await handleLoadConfig(pendingConfigForPromptOverwrite, overwrite);
        setPendingConfigForPromptOverwrite(null);
        setShowPromptOverwriteDialog(false);
      }
    },
    [pendingConfigForPromptOverwrite, handleLoadConfig]
  );

  const handlePromptOverwriteCancel = useCallback(() => {
    if (pendingConfigForPromptOverwrite) {
      setExperimentConfig(pendingConfigForPromptOverwrite);
      setConfigModeActive(true);
      hasUnsavedChangesRef.current = true;
      setSaveStatus("unsaved");

      if (notebookId) {
        refetchNotebookHistory();
      }
    }
    setPendingConfigForPromptOverwrite(null);
    setShowPromptOverwriteDialog(false);
  }, [pendingConfigForPromptOverwrite, notebookId, refetchNotebookHistory, hasUnsavedChangesRef, setSaveStatus]);

  return {
    configModeActive,
    setConfigModeActive,
    experimentConfig,
    setExperimentConfig,
    experimentRuns,
    setExperimentRuns,
    createExperimentModalOpen,
    setCreateExperimentModalOpen,
    showPromptOverwriteDialog,
    pendingConfigForPromptOverwrite,
    handleLoadConfig,
    handleCreateNewConfig,
    handleCreateExperimentSubmit,
    handlePromptOverwriteConfirm,
    handlePromptOverwriteCancel,
  };
}
