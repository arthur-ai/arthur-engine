import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import LaunchIcon from "@mui/icons-material/Launch";
import { Box, Typography, Chip, LinearProgress, Card, CardContent, Tooltip, Button, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, IconButton, Link } from "@mui/material";
import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";

import { CreateExperimentModal, ExperimentFormData } from "./CreateExperimentModal";
import { ExperimentResultsTable } from "./ExperimentResultsTable";
import { PromptVersionDrawer } from "./PromptVersionDrawer";

import { getContentHeight } from "@/constants/layout";
import { usePromptExperiment, useCreateExperiment, useDeleteExperiment } from "@/hooks/usePromptExperiments";
import { useCreateNotebookMutation, useAttachExperimentToNotebookMutation, useSetNotebookStateMutation } from "@/hooks/useNotebooks";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";
import { formatUTCTimestamp, formatTimestampDuration, formatCurrency } from "@/utils/formatters";

interface PromptVersionDetails {
  prompt_key?: string | null; // Format: "saved:name:version" or "unsaved:auto_name"
  prompt_type?: string | null; // "saved" or "unsaved"
  prompt_name?: string | null; // For saved prompts or auto_name for unsaved
  prompt_version?: string | null; // For saved prompts only
  eval_results: Array<{
    eval_name: string;
    eval_version: string;
    pass_count: number;
    total_count: number;
  }>;
}

export const ExperimentDetailView: React.FC = () => {
  const { id: taskId, experimentId } = useParams<{ id: string; experimentId: string }>();
  const navigate = useNavigate();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptVersionDetails | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Disable query when deleting to prevent refetch attempts
  const { experiment, isLoading, error, refetch } = usePromptExperiment(experimentId, !isDeleting);
  const createExperiment = useCreateExperiment(taskId);
  const deleteExperiment = useDeleteExperiment();
  const createNotebook = useCreateNotebookMutation(taskId);
  const attachExperimentToNotebook = useAttachExperimentToNotebookMutation();
  const setNotebookState = useSetNotebookStateMutation();

  const handlePromptClick = (promptSummary: PromptVersionDetails) => {
    setSelectedPrompt(promptSummary);
    setDrawerOpen(true);
  };

  const handleDrawerClose = () => {
    setDrawerOpen(false);
  };

  const handleOpenInNotebook = async (promptName: string, promptVersion: string, event: React.MouseEvent) => {
    // Prevent the card click event from firing
    event.stopPropagation();

    if (!experiment || !experimentId || !taskId) return;

    try {
      let notebookId = experiment.notebook_id;

      // Create notebook if it doesn't exist
      if (!notebookId) {
        const notebook = await createNotebook.mutateAsync({
          name: `${experiment.name} - Notebook`,
          description: `Notebook for experiment: ${experiment.name}`,
        });

        // Attach the experiment to the newly created notebook
        await attachExperimentToNotebook.mutateAsync({
          experimentId,
          notebookId: notebook.id,
        });

        notebookId = notebook.id;
      }

      // Save the experiment config to the notebook state
      await setNotebookState.mutateAsync({
        notebookId,
        request: {
          state: {
            prompt_configs: experiment.prompt_configs || null,
            prompt_variable_mapping: experiment.prompt_variable_mapping || null,
            dataset_ref: experiment.dataset_ref
              ? {
                  id: experiment.dataset_ref.id,
                  name: experiment.dataset_ref.name,
                  version: experiment.dataset_ref.version,
                }
              : null,
            eval_list: experiment.eval_list || null,
            dataset_row_filter: experiment.dataset_row_filter && experiment.dataset_row_filter.length > 0
              ? experiment.dataset_row_filter
              : null,
          },
        },
      });

      // Navigate to the notebook with experiment config loaded
      navigate(`/tasks/${taskId}/playgrounds/prompts?notebookId=${notebookId}&experimentId=${experimentId}`);
    } catch (error) {
      console.error("Failed to open in notebook:", error);
    }
  };


  // Refetch data when window gains focus (but not if we're deleting)
  useEffect(() => {
    const handleFocus = () => {
      if (!isDeleting) {
        refetch();
      }
    };

    window.addEventListener("focus", handleFocus);
    return () => {
      window.removeEventListener("focus", handleFocus);
    };
  }, [refetch, isDeleting]);

  // Auto-refresh when experiment is running (but not if we're deleting)
  useEffect(() => {
    // Check if experiment is in a running state (queued or running)
    const isExperimentRunning = experiment?.status === "running" || experiment?.status === "queued";

    if (!isExperimentRunning || isDeleting) {
      return;
    }

    // Set up interval to refresh every 1 second
    const intervalId = setInterval(() => {
      if (!isDeleting) {
        refetch();
        setRefreshTrigger((prev) => prev + 1);
      }
    }, 1000);

    // Clean up interval when component unmounts or experiment stops running
    return () => {
      clearInterval(intervalId);
    };
  }, [experiment?.status, refetch, isDeleting]);

  const getStatusColor = (status: PromptExperimentDetail["status"]): "default" | "primary" | "info" | "success" | "error" => {
    switch (status) {
      case "queued":
        return "default";
      case "running":
        return "primary";
      case "completed":
        return "success";
      case "failed":
        return "error";
      default:
        return "default";
    }
  };

  const getStatusLabel = (status: PromptExperimentDetail["status"]): string => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  const handleCreateFromExisting = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleDeleteClick = () => {
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteCancel = () => {
    setIsDeleteDialogOpen(false);
  };

  const handleDeleteConfirm = async () => {
    if (!experimentId) return;

    try {
      setIsDeleting(true);
      await deleteExperiment.mutateAsync(experimentId);
      setIsDeleteDialogOpen(false);
      // Navigate back to experiments list after successful deletion
      navigate(`/tasks/${taskId}/prompt-experiments`);
    } catch (err) {
      console.error("Failed to delete experiment:", err);
      setIsDeleting(false);
      // Keep dialog open on error so user can see the error
    }
  };

  const handleSubmitExperiment = async (data: ExperimentFormData): Promise<{ id: string }> => {
    // Validate that datasetVersion is a number
    if (typeof data.datasetVersion !== "number") {
      throw new Error("Dataset version must be selected");
    }

    try {
      // Transform prompt variable mappings to API format
      const promptVariableMapping = Object.entries(data.promptVariableMappings || {}).map(([varName, columnName]) => ({
        variable_name: varName,
        source: {
          type: "dataset_column" as const,
          dataset_column: {
            name: columnName,
          },
        },
      }));

      // Transform eval variable mappings to API format
      const evalList = data.evaluators.map((evaluator) => {
        const evalMapping = data.evalVariableMappings?.find((m) => m.evalName === evaluator.name && m.evalVersion === evaluator.version);

        const variableMapping = evalMapping
          ? Object.entries(evalMapping.mappings).map(([varName, mapping]) => {
              if (mapping.sourceType === "dataset_column") {
                return {
                  variable_name: varName,
                  source: {
                    type: "dataset_column" as const,
                    dataset_column: {
                      name: mapping.datasetColumn || "",
                    },
                  },
                };
              } else {
                return {
                  variable_name: varName,
                  source: {
                    type: "experiment_output" as const,
                    experiment_output: {
                      json_path: mapping.jsonPath || null,
                    },
                  },
                };
              }
            })
          : [];

        return {
          name: evaluator.name,
          version: evaluator.version,
          variable_mapping: variableMapping,
        };
      });

      const result = await createExperiment.mutateAsync({
        name: data.name,
        description: data.description,
        dataset_ref: {
          id: data.datasetId,
          version: data.datasetVersion,
        },
        prompt_configs: data.promptVersions.map(pv => ({
          type: "saved" as const,
          name: pv.promptName,
          version: pv.version,
        })),
        prompt_variable_mapping: promptVariableMapping,
        eval_list: evalList,
        dataset_row_filter: data.datasetRowFilter && data.datasetRowFilter.length > 0 ? data.datasetRowFilter : undefined,
      });
      handleCloseModal();
      return { id: result.id };
    } catch (err) {
      console.error("Failed to create experiment:", err);
      throw err;
    }
  };

  const getStatusChipSx = (color: "default" | "primary" | "info" | "success" | "error") => {
    const colorMap = {
      default: { color: "text.secondary", borderColor: "text.secondary" },
      primary: { color: "primary.main", borderColor: "primary.main" },
      info: { color: "info.main", borderColor: "info.main" },
      success: { color: "success.main", borderColor: "success.main" },
      error: { color: "error.main", borderColor: "error.main" },
    };
    return {
      backgroundColor: "transparent",
      color: colorMap[color].color,
      borderColor: colorMap[color].borderColor,
      borderWidth: 1,
      borderStyle: "solid",
    };
  };

  if (isLoading) {
    return (
      <Box className="flex items-center justify-center h-full">
        <Typography>Loading experiment...</Typography>
      </Box>
    );
  }

  if (error || !experiment) {
    return (
      <Box className="flex items-center justify-center h-full">
        <Typography color="error">{error?.message || "Experiment not found"}</Typography>
      </Box>
    );
  }

  return (
    <Box className="w-full overflow-auto" style={{ height: getContentHeight() }}>
      <Box className="p-6">
        {/* Breadcrumb / Back Button */}
        <Box className="mb-4">
          <Box
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 cursor-pointer w-fit"
            onClick={() => navigate(`/tasks/${taskId}/prompt-experiments`)}
          >
            <ArrowBackIcon fontSize="small" />
            <Typography variant="body2" className="font-medium">
              Back to Experiments
            </Typography>
          </Box>
        </Box>

        {/* Header Section */}
        <Box className="mb-6">
          <Box className="flex items-center justify-between mb-2">
            <Box className="flex items-center gap-3">
              <Typography variant="h4" className="font-semibold text-gray-900">
                {experiment.name}
              </Typography>
              <Chip label={getStatusLabel(experiment.status)} size="small" sx={getStatusChipSx(getStatusColor(experiment.status))} />
            </Box>
            <Box className="flex items-center gap-2">
              <Button variant="outlined" startIcon={<ContentCopyIcon />} onClick={handleCreateFromExisting}>
                Copy to new experiment
              </Button>
              <Button variant="outlined" color="error" startIcon={<DeleteIcon />} onClick={handleDeleteClick}>
                Delete
              </Button>
            </Box>
          </Box>
          {experiment.description && (
            <Typography variant="body1" className="text-gray-600 mb-4">
              {experiment.description}
            </Typography>
          )}
          <Box className="flex gap-6 text-sm text-gray-600">
            <Box>
              <span className="font-medium">Created:</span> {formatUTCTimestamp(experiment.created_at)}
            </Box>
            <Box>
              <span className="font-medium">Finished:</span> {formatUTCTimestamp(experiment.finished_at)}
            </Box>
            {experiment.finished_at &&
              (() => {
                const duration = formatTimestampDuration(experiment.created_at, experiment.finished_at);
                return duration ? (
                  <Box>
                    <span className="font-medium">Duration:</span> {duration}
                  </Box>
                ) : null;
              })()}
            <Box>
              <span className="font-medium">Prompts:</span> {experiment.prompt_configs.length} prompt{experiment.prompt_configs.length > 1 ? 's' : ''}
            </Box>
            <Box>
              <span className="font-medium">Dataset:</span>{" "}
              <Link
                component={RouterLink}
                to={`/tasks/${taskId}/datasets/${experiment.dataset_ref.id}?version=${experiment.dataset_ref.version}`}
                underline="hover"
                sx={{ cursor: "pointer" }}
              >
                {experiment.dataset_ref.name} (v{experiment.dataset_ref.version})
              </Link>
            </Box>
            {experiment.total_cost && (
              <Box>
                <span className="font-medium">Total Cost:</span> {formatCurrency(parseFloat(experiment.total_cost))}
              </Box>
            )}
          </Box>

          {/* Dataset Row Filter Section */}
          {experiment.dataset_row_filter && experiment.dataset_row_filter.length > 0 && (
            <Box className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded">
              <Box className="flex items-center gap-2 mb-2">
                <Typography variant="body2" className="font-medium text-gray-900">
                  Dataset Row Filter Applied
                </Typography>
                <Tooltip
                  title="This experiment only includes dataset rows that match ALL of the following conditions."
                  arrow
                  placement="right"
                >
                  <InfoOutlinedIcon
                    sx={{
                      fontSize: 16,
                      color: "text.secondary",
                      cursor: "help",
                    }}
                  />
                </Tooltip>
              </Box>
              <Box className="flex flex-wrap gap-2">
                {experiment.dataset_row_filter.map((filter, index) => (
                  <Chip
                    key={index}
                    label={`${filter.column_name} = "${filter.column_value}"`}
                    size="small"
                    variant="outlined"
                    sx={{
                      backgroundColor: "white",
                      borderColor: "#3b82f6",
                      color: "#1e40af",
                    }}
                  />
                ))}
              </Box>
            </Box>
          )}
        </Box>

        {/* Overall Prompt Performance Section */}
        <Box className="mb-6">
          <Box className="flex items-center gap-2 mb-4">
            <Typography variant="h5" className="font-semibold text-gray-900">
              Overall Prompt Performance
            </Typography>
            <Tooltip
              title="Each tile shows the evaluation results for a specific prompt version. The progress bars indicate how many test cases passed for each evaluator."
              arrow
              placement="right"
            >
              <InfoOutlinedIcon
                sx={{
                  fontSize: 20,
                  color: "text.secondary",
                  cursor: "help",
                }}
              />
            </Tooltip>
          </Box>

          {experiment.summary_results.prompt_eval_summaries.length === 0 ? (
            <Box className="p-6 bg-gray-50 border border-gray-200 rounded">
              <Typography variant="body1" className="text-gray-600 italic">
                Overall performance will be shown when the experiment finishes executing test cases.
              </Typography>
            </Box>
          ) : (
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
              {(() => {
                const sortedSummaries = [...experiment.summary_results.prompt_eval_summaries].sort((a, b) => {
                  // Calculate total passes for each prompt
                  const totalPassesA = a.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const totalPassesB = b.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);

                  // Sort by total passes descending
                  if (totalPassesB !== totalPassesA) {
                    return totalPassesB - totalPassesA;
                  }

                  // If tied, sort by version descending (higher version first)
                  return parseInt(b.prompt_version || "0") - parseInt(a.prompt_version || "0");
                });

                // Find the max total passes to identify best performing prompts
                const maxTotalPasses =
                  sortedSummaries.length > 0
                    ? Math.max(...sortedSummaries.map((summary) => summary.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0)))
                    : 0;

                return sortedSummaries.map((promptSummary) => {
                  const totalPasses = promptSummary.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const isBestPerforming = totalPasses === maxTotalPasses;

                  // Get display name for prompt
                  const promptDisplayName = (promptSummary.prompt_type === "saved" || !promptSummary.prompt_type)
                    ? `${promptSummary.prompt_name} (v${promptSummary.prompt_version})`
                    : promptSummary.prompt_name || "Unsaved Prompt";

                  return (
                    <Card
                      key={promptSummary.prompt_key || `${promptSummary.prompt_name}-${promptSummary.prompt_version}`}
                      elevation={1}
                      onClick={() => handlePromptClick(promptSummary)}
                      sx={{ cursor: "pointer", "&:hover": { boxShadow: 3 }, position: "relative" }}
                    >
                      <CardContent sx={{ position: "relative", paddingBottom: "40px !important", minHeight: "200px" }}>
                        <Box className="flex items-center gap-2 mb-3">
                          <Typography variant="subtitle1" className="font-medium text-gray-800 truncate flex-1 min-w-0">
                            Prompt: {promptDisplayName}
                          </Typography>
                          {promptSummary.prompt_type === "unsaved" && (
                            <Chip label="Unsaved" size="small" sx={{ backgroundColor: "#fff3e0", color: "#f57c00", fontWeight: 600 }} className="shrink-0" />
                          )}
                          {isBestPerforming && <Chip label="Best" size="small" color="success" sx={{ fontWeight: 600 }} className="shrink-0" />}
                        </Box>

                        <Box className="space-y-3">
                          {promptSummary.eval_results.map((evalResult) => {
                            const percentage = (evalResult.pass_count / evalResult.total_count) * 100;

                            return (
                              <Box key={`${evalResult.eval_name}-${evalResult.eval_version}`}>
                                <Box className="flex justify-between items-center mb-1">
                                  <Typography variant="caption" className="font-medium text-gray-700">
                                    {evalResult.eval_name} (v{evalResult.eval_version})
                                  </Typography>
                                  <Typography variant="caption" className="text-gray-600">
                                    {percentage.toFixed(0)}%
                                  </Typography>
                                </Box>
                                <LinearProgress
                                  variant="determinate"
                                  value={percentage}
                                  className="h-2 rounded"
                                  sx={{
                                    backgroundColor: "#ef4444",
                                    "& .MuiLinearProgress-bar": {
                                      backgroundColor: "#10b981",
                                    },
                                  }}
                                />
                                <Typography variant="caption" className="text-gray-500 text-xs">
                                  {evalResult.pass_count} / {evalResult.total_count} test cases passed
                                </Typography>
                              </Box>
                            );
                          })}
                        </Box>

                        {/* Open in Notebook button in lower left corner - only for saved prompts */}
                        {(promptSummary.prompt_type === "saved" || !promptSummary.prompt_type) && promptSummary.prompt_name && promptSummary.prompt_version && (
                          <Button
                            size="small"
                            startIcon={<LaunchIcon />}
                            onClick={(e) => handleOpenInNotebook(promptSummary.prompt_name!, promptSummary.prompt_version!, e)}
                            sx={{
                              position: "absolute",
                              bottom: 8,
                              left: 8,
                              textTransform: 'none',
                              fontSize: '0.75rem',
                              color: 'text.secondary',
                              '&:hover': {
                                backgroundColor: 'rgba(0, 0, 0, 0.04)',
                              },
                            }}
                          >
                            Open in Notebook
                          </Button>
                        )}

                        {/* Expand icon in lower right corner */}
                        <Box
                          sx={{
                            position: "absolute",
                            bottom: 8,
                            right: 8,
                            opacity: 0.4,
                            transition: "opacity 0.2s",
                          }}
                        >
                          <OpenInFullIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                        </Box>
                      </CardContent>
                    </Card>
                  );
                });
              })()}
            </Box>
          )}
        </Box>

        {/* Test Case Results Section */}
        <Box className="mb-6">
          <Box className="flex items-center gap-2 mb-4">
            <Typography variant="h5" className="font-semibold text-gray-900">
              Test Case Results
            </Typography>
            <Tooltip
              title="This table shows individual test case results. Each row represents one test case from your dataset, showing pass/fail for each prompt version and evaluator combination."
              arrow
              placement="right"
            >
              <InfoOutlinedIcon
                sx={{
                  fontSize: 20,
                  color: "text.secondary",
                  cursor: "help",
                }}
              />
            </Tooltip>
          </Box>
          {taskId && experimentId && (
            <ExperimentResultsTable
              taskId={taskId}
              experimentId={experimentId}
              refreshTrigger={refreshTrigger}
              datasetId={experiment.dataset_ref.id}
              datasetVersion={experiment.dataset_ref.version}
              promptSummaries={(() => {
                // Sort prompt summaries the same way as in Overall Prompt Performance
                const sorted = [...experiment.summary_results.prompt_eval_summaries].sort((a, b) => {
                  const totalPassesA = a.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const totalPassesB = b.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  if (totalPassesB !== totalPassesA) {
                    return totalPassesB - totalPassesA;
                  }
                  return parseInt(b.prompt_version || "0") - parseInt(a.prompt_version || "0");
                });
                return sorted;
              })()}
            />
          )}
        </Box>
      </Box>

      {/* Create from Existing Modal */}
      <CreateExperimentModal open={isModalOpen} onClose={handleCloseModal} onSubmit={handleSubmitExperiment} initialData={experiment} />

      {/* Prompt Version Drawer */}
      {taskId && experimentId && (
        <PromptVersionDrawer
          open={drawerOpen}
          onClose={handleDrawerClose}
          promptDetails={selectedPrompt}
          taskId={taskId}
          experimentId={experimentId}
          experimentPromptConfigs={experiment.prompt_configs}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onClose={handleDeleteCancel}>
        <DialogTitle>Delete Experiment</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the experiment "{experiment?.name}"? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel} disabled={deleteExperiment.isPending}>
            Cancel
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained" disabled={deleteExperiment.isPending}>
            {deleteExperiment.isPending ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
