import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import { useSnackbar } from "notistack";
import { useQueryStates } from "nuqs";
import { useReducer, useEffect, useRef, useState, useMemo } from "react";

import ExperimentConfigDrawer from "./ExperimentConfigDrawer";
import { useExperimentConfig } from "./hooks/useExperimentConfig";
import { useExperimentExecution } from "./hooks/useExperimentExecution";
import { useFetchBackendPrompts } from "./hooks/useFetchBackendPrompts";
import { useNotebookAutoSave } from "./hooks/useNotebookAutoSave";
import PlaygroundHeader from "./PlaygroundHeader";
import PromptComponent from "./prompts/PromptComponent";
import { PromptProvider } from "./PromptsPlaygroundContext";
import { playgroundParams } from "./PromptsPlaygroundWrapper";
import { promptsReducer, buildInitialReducerState } from "./reducer";
import SetConfigDrawer from "./SetConfigDrawer";
import { PlaygroundInitialData } from "./types";

import { CreateExperimentModal } from "@/components/prompt-experiments/CreateExperimentModal";
import { useModelProviders, useAvailableModels } from "@/hooks/useModelProviders";
import { useNotebookHistory } from "@/hooks/useNotebooks";
import { useTask } from "@/hooks/useTask";
import { PromptVariableMappingOutput } from "@/lib/api-client/api-client";
import { track, EVENT_NAMES } from "@/services/amplitude";

const PromptsPlayground = ({ initialData }: { initialData: PlaygroundInitialData }) => {
  const [state, dispatch] = useReducer(promptsReducer, initialData, buildInitialReducerState);
  const { enqueueSnackbar } = useSnackbar();
  const { task } = useTask();
  const fetchPrompts = useFetchBackendPrompts();

  const [params] = useQueryStates(playgroundParams);
  const { notebookId } = params;

  const [saveStatus, setSaveStatus] = useState<"saved" | "saving" | "unsaved">("saved");
  const hasUnsavedChangesRef = useRef<boolean>(false);

  const { experiments: notebookHistory, refetch: refetchNotebookHistory } = useNotebookHistory(notebookId ?? undefined, 0, 100);

  const config = useExperimentConfig({
    initialData,
    state,
    dispatch,
    notebookId,
    hasUnsavedChangesRef,
    setSaveStatus,
    refetchNotebookHistory,
  });

  const autoSave = useNotebookAutoSave({
    notebookId,
    initialName: initialData.notebookName,
    initialBaseline: initialData.autoSaveBaseline,
    state,
    experimentConfig: config.experimentConfig,
    saveStatus,
    setSaveStatus,
    hasUnsavedChangesRef,
  });

  const execution = useExperimentExecution({
    experimentConfig: config.experimentConfig,
    setExperimentRuns: config.setExperimentRuns,
    configModeActive: config.configModeActive,
    state,
    dispatch,
    notebookId,
    refetchNotebookHistory,
  });

  const { providers: enabledProviders } = useModelProviders();
  const { availableModels } = useAvailableModels(enabledProviders);

  const didMountRef = useRef(false);
  useEffect(() => {
    if (didMountRef.current) return;
    didMountRef.current = true;

    if (initialData.source.type === "blank") return;
    track(EVENT_NAMES.NOTEBOOK_LOADED, {
      notebook_id: notebookId,
      prompt_count: initialData.prompts.length,
      has_config: !!initialData.experimentConfig,
    });
    if (initialData.source.label) {
      enqueueSnackbar(initialData.source.label, { variant: "info", autoHideDuration: 3000 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchPrompts(dispatch);
  }, [fetchPrompts]);

  const [configDrawerOpen, setConfigDrawerOpen] = useState(false);
  const toggleConfigDrawer = () => setConfigDrawerOpen((prev) => !prev);

  const handleAddPrompt = () => {
    dispatch({ type: "addPrompt" });
  };

  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      if (e.shiftKey) {
        e.preventDefault();
        container.scrollLeft += e.deltaX || e.deltaY;
      }
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      container.removeEventListener("wheel", handleWheel);
    };
  }, []);

  const blankVariablesCount = useMemo(() => {
    if (config.experimentConfig?.prompt_variable_mapping) {
      const mappedVariables = new Set<string>();
      config.experimentConfig.prompt_variable_mapping.forEach((mapping: PromptVariableMappingOutput) => {
        mappedVariables.add(mapping.variable_name);
      });

      let count = 0;
      state.keywords.forEach((value, key) => {
        if (!mappedVariables.has(key) && (!value || value.trim() === "")) {
          count++;
        }
      });
      return count;
    }

    let count = 0;
    state.keywords.forEach((value) => {
      if (!value || value.trim() === "") {
        count++;
      }
    });
    return count;
  }, [state.keywords, config.experimentConfig]);

  const allPromptsHaveModelConfig = useMemo(() => {
    return state.prompts.every((prompt) => prompt.modelProvider !== "" && prompt.modelName !== "");
  }, [state.prompts]);

  const runAllDisabledReason = useMemo(() => {
    if (!allPromptsHaveModelConfig) {
      return "All prompts must have a model provider and model selected";
    }
    if (blankVariablesCount > 0) {
      return "Please fill in all variable values before running";
    }
    if (execution.isRunningExperiment) {
      return "An experiment is currently running";
    }
    return null;
  }, [allPromptsHaveModelConfig, blankVariablesCount, execution.isRunningExperiment]);

  const shouldHighlightCosts = useMemo(() => {
    if (state.prompts.length < 2) return false;
    return state.prompts.some((prompt) => {
      const cost = prompt.runResponse?.cost;
      return cost && cost !== "-" && cost !== "0.000000" && parseFloat(cost) > 0;
    });
  }, [state.prompts]);

  const drawerRuns = notebookId ? notebookHistory : config.experimentRuns;

  return (
    <PromptProvider
      state={state}
      dispatch={dispatch}
      enabledProviders={enabledProviders}
      availableModels={availableModels}
      experimentConfig={config.experimentConfig}
      handleRunSingleWithConfig={execution.handleRunSingleWithConfig}
      isRunningExperiment={execution.isRunningExperiment}
      runningExperimentId={execution.runningExperimentId}
      lastCompletedExperimentId={execution.lastCompletedExperimentId}
    >
      <Box className="flex flex-col h-full" sx={{ position: "relative", backgroundColor: "background.default" }}>
        <PlaygroundHeader
          notebookId={notebookId}
          isRenaming={autoSave.isRenaming}
          newNotebookName={autoSave.newNotebookName}
          setNewNotebookName={autoSave.setNewNotebookName}
          saveStatus={autoSave.saveStatus}
          notebookName={autoSave.notebookName}
          onStartRename={autoSave.handleStartRename}
          onSaveRename={autoSave.handleSaveRename}
          onCancelRename={autoSave.handleCancelRename}
          onManualSave={() => autoSave.autoSaveNotebookState("manual")}
          configDrawerOpen={configDrawerOpen}
          configModeActive={config.configModeActive}
          experimentConfig={config.experimentConfig}
          onToggleConfigDrawer={toggleConfigDrawer}
          blankVariablesCount={blankVariablesCount}
          onAddPrompt={handleAddPrompt}
          runAllDisabledReason={runAllDisabledReason}
          onRunAllPrompts={execution.handleRunAllPrompts}
        />

        <Box component="main" className="flex-1 flex flex-col">
          <Box ref={scrollContainerRef} className="flex-1 overflow-x-auto overflow-y-auto p-1">
            <Stack direction="row" spacing={1} sx={{ height: "100%" }}>
              {state.prompts.map((prompt) => {
                const promptHasCost = !!(
                  prompt.runResponse?.cost &&
                  prompt.runResponse.cost !== "-" &&
                  prompt.runResponse.cost !== "0.000000" &&
                  parseFloat(prompt.runResponse.cost) > 0
                );
                const highlightThisPrompt = shouldHighlightCosts && promptHasCost;

                return (
                  <Box key={prompt.id} className="flex-1 h-full" sx={{ minWidth: 400 }}>
                    <PromptComponent prompt={prompt} useIconOnlyMode={false} highlightCost={highlightThisPrompt} />
                  </Box>
                );
              })}
            </Stack>
          </Box>
        </Box>

        {!config.configModeActive || !config.experimentConfig ? (
          <SetConfigDrawer
            open={configDrawerOpen}
            onClose={toggleConfigDrawer}
            taskId={task?.id}
            onLoadConfig={config.handleLoadConfig}
            onCreateNewConfig={config.handleCreateNewConfig}
            hasExistingPrompts={state.prompts.length > 0}
          />
        ) : (
          <ExperimentConfigDrawer
            open={configDrawerOpen}
            onClose={toggleConfigDrawer}
            experimentConfig={config.experimentConfig}
            notebookId={notebookId}
            runs={drawerRuns}
            expandedRunId={execution.expandedRunId}
            runDetails={execution.runDetails}
            onExpandRun={execution.handleExpandRun}
          />
        )}

        <CreateExperimentModal
          open={config.createExperimentModalOpen}
          onClose={() => config.setCreateExperimentModalOpen(false)}
          onSubmit={config.handleCreateExperimentSubmit}
          disableNavigation={true}
        />

        <Dialog open={config.showPromptOverwriteDialog} onClose={config.handlePromptOverwriteCancel} maxWidth="sm" fullWidth>
          <DialogTitle>Overwrite Existing Prompts?</DialogTitle>
          <DialogContent>
            <DialogContentText>
              This notebook already contains prompts. Would you like to overwrite them with the prompts from the selected configuration, or keep your
              existing prompts and only load the configuration?
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={config.handlePromptOverwriteCancel} color="inherit">
              Cancel
            </Button>
            <Button onClick={() => config.handlePromptOverwriteConfirm(false)} variant="outlined">
              Keep Existing Prompts
            </Button>
            <Button onClick={() => config.handlePromptOverwriteConfirm(true)} variant="contained" color="primary">
              Overwrite Prompts
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </PromptProvider>
  );
};

export default PromptsPlayground;
