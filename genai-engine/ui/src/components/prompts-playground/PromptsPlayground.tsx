import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import { alpha } from "@mui/material/styles";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useReducer, useEffect, useRef, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useNavigate } from "react-router-dom";
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
      triggerNotebookSave={autoSave.requestImmediateSave}
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
                    {/* Experiment Name Section - Only show if not in notebook mode */}
                    {!notebookId && experimentConfig.id && (
                      <>
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
                              onClick={() => navigate(`/tasks/${task?.id}/prompt-experiments/${experimentConfig.id}`)}
                              sx={{
                                padding: 0.5,
                                color: "text.disabled",
                                "&:hover": {
                                  color: "text.secondary",
                                  backgroundColor: "action.hover",
                                },
                              }}
                            >
                              <OpenInNewIcon sx={{ fontSize: "0.875rem" }} />
                            </IconButton>
                          </Box>
                        </Box>

                        <Divider />
                      </>
                    )}

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
                              onClick={() => {
                                if (experimentConfig.dataset_ref?.id && task?.id) {
                                  navigate(`/tasks/${task.id}/datasets/${experimentConfig.dataset_ref.id}`);
                                }
                              }}
                              sx={{
                                padding: 0.5,
                                color: "text.disabled",
                                "&:hover": {
                                  color: "text.secondary",
                                  backgroundColor: "action.hover",
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
                    {experimentConfig.prompt_variable_mapping && experimentConfig.prompt_variable_mapping.length > 0 && (
                      <>
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: "text.secondary" }}>
                            PROMPT VARIABLE MAPPINGS
                          </Typography>
                          <Stack spacing={1}>
                            {experimentConfig.prompt_variable_mapping.map((mapping: PromptVariableMappingOutput, idx: number) => (
                              <Box
                                key={idx}
                                sx={{
                                  backgroundColor: (theme) => alpha(theme.palette.info.main, 0.12),
                                  borderLeft: (theme) => `3px solid ${theme.palette.info.main}`,
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
                                  <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "info.main" }}>
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
                            {experimentConfig.eval_list.map((evalRef: EvalRefOutput, evalIdx: number) => (
                              <Box key={evalIdx}>
                                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}>
                                  <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.813rem" }}>
                                    {evalRef.name}{" "}
                                    <Box component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>
                                      (v{evalRef.version})
                                    </Box>
                                  </Typography>
                                  <IconButton
                                    size="small"
                                    onClick={() => navigate(`/tasks/${task?.id}/evaluators/${encodeURIComponent(evalRef.name)}`)}
                                    sx={{
                                      padding: 0.25,
                                      color: "text.disabled",
                                      "&:hover": {
                                        color: "text.secondary",
                                        backgroundColor: "action.hover",
                                      },
                                    }}
                                  >
                                    <OpenInNewIcon sx={{ fontSize: "0.75rem" }} />
                                  </IconButton>
                                </Box>
                                <Stack spacing={1}>
                                  {evalRef.variable_mapping?.map((mapping: EvalVariableMappingOutput, mapIdx: number) => {
                                    const isDatasetColumn = mapping.source?.type === "dataset_column";
                                    return (
                                      <Box
                                        key={mapIdx}
                                        sx={{
                                          backgroundColor: (theme) =>
                                            alpha(isDatasetColumn ? theme.palette.info.main : theme.palette.warning.main, 0.12),
                                          borderLeft: (theme) =>
                                            `3px solid ${isDatasetColumn ? theme.palette.info.main : theme.palette.warning.main}`,
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
                                          {isDatasetColumn && mapping.source?.type === "dataset_column" ? (
                                            <>
                                              Dataset column:{" "}
                                              <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "info.main" }}>
                                                {mapping.source.dataset_column?.name}
                                              </Box>
                                            </>
                                          ) : (
                                            <>
                                              Experiment output
                                              {mapping.source?.type === "experiment_output" && mapping.source.experiment_output?.json_path && (
                                                <>
                                                  {" "}
                                                  (path:{" "}
                                                  <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "warning.main" }}>
                                                    {mapping.source.experiment_output.json_path}
                                                  </Box>
                                                  )
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

                    {/* Experiment Runs Section - Show notebook history if in notebook mode */}
                    {(notebookId ? notebookHistory : experimentRuns).length > 0 && (
                      <Box>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: "text.secondary" }}>
                          EXPERIMENT HISTORY ({notebookId ? notebookHistory.length : experimentRuns.length})
                        </Typography>
                        <Stack spacing={1}>
                          {(notebookId ? notebookHistory : experimentRuns).map((run: PromptExperimentSummary, idx: number) => {
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
                                  backgroundColor: (theme) =>
                                    isCompleted
                                      ? alpha(theme.palette.success.main, 0.08)
                                      : isFailed
                                        ? alpha(theme.palette.error.main, 0.08)
                                        : "background.paper",
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
                                        backgroundColor: (theme) =>
                                          isCompleted
                                            ? theme.palette.success.main
                                            : isFailed
                                              ? theme.palette.error.main
                                              : isRunning
                                                ? theme.palette.warning.main
                                                : theme.palette.grey[600],
                                        color: (theme) =>
                                          isCompleted
                                            ? theme.palette.success.contrastText
                                            : isFailed
                                              ? theme.palette.error.contrastText
                                              : isRunning
                                                ? theme.palette.warning.contrastText
                                                : theme.palette.common.white,
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
                                      backgroundColor: (theme) => (theme.palette.mode === "dark" ? "rgba(255,255,255,0.02)" : "rgba(0,0,0,0.02)"),
                                    }}
                                  >
                                    <Stack spacing={1.5}>
                                      {details.summary_results.prompt_eval_summaries.map((promptSummary: PromptEvalResultSummaries, pIdx: number) => (
                                        <Box key={pIdx}>
                                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 0.75 }}>
                                            <Typography variant="body2" sx={{ fontWeight: 600, fontSize: "0.75rem" }}>
                                              {promptSummary.prompt_name}{" "}
                                              <Box component="span" sx={{ fontWeight: 400, color: "text.secondary" }}>
                                                (v{promptSummary.prompt_version})
                                              </Box>
                                            </Typography>
                                            <IconButton
                                              size="small"
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                if (promptSummary.prompt_name && promptSummary.prompt_version && task?.id) {
                                                  navigate(
                                                    `/tasks/${task.id}/prompts/${encodeURIComponent(promptSummary.prompt_name)}/versions/${promptSummary.prompt_version}`
                                                  );
                                                }
                                              }}
                                              sx={{
                                                padding: 0.25,
                                                color: "text.disabled",
                                                "&:hover": {
                                                  color: "text.secondary",
                                                  backgroundColor: "action.hover",
                                                },
                                              }}
                                            >
                                              <OpenInNewIcon sx={{ fontSize: "0.65rem" }} />
                                            </IconButton>
                                          </Box>
                                          <Stack spacing={0.75}>
                                            {promptSummary.eval_results.map((evalResult: EvalResultSummary, eIdx: number) => {
                                              const percentage =
                                                evalResult.total_count > 0 ? (evalResult.pass_count / evalResult.total_count) * 100 : 0;
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
