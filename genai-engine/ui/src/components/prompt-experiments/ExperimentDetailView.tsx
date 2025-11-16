import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { Box, Typography, Chip, LinearProgress, Card, CardContent, IconButton, Tooltip, Button } from "@mui/material";
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { CreateExperimentModal, ExperimentFormData } from "./CreateExperimentModal";
import { ExperimentResultsTable } from "./ExperimentResultsTable";

import { getContentHeight } from "@/constants/layout";
import { usePromptExperiment, useCreateExperiment } from "@/hooks/usePromptExperiments";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";
import { formatUTCTimestamp, formatTimestampDuration, formatCurrency } from "@/utils/formatters";

export const ExperimentDetailView: React.FC = () => {
  const { id: taskId, experimentId } = useParams<{ id: string; experimentId: string }>();
  const navigate = useNavigate();
  const { experiment, isLoading, error, refetch } = usePromptExperiment(experimentId);
  const createExperiment = useCreateExperiment(taskId);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Refetch data when window gains focus
  useEffect(() => {
    const handleFocus = () => {
      refetch();
    };

    window.addEventListener("focus", handleFocus);
    return () => {
      window.removeEventListener("focus", handleFocus);
    };
  }, [refetch]);

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

  const handleSubmitExperiment = async (data: ExperimentFormData): Promise<{ id: string }> => {
    // Validate that datasetVersion is a number
    if (typeof data.datasetVersion !== 'number') {
      throw new Error('Dataset version must be selected');
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
      const evalList = data.evaluators.map(evaluator => {
        const evalMapping = data.evalVariableMappings?.find(
          m => m.evalName === evaluator.name && m.evalVersion === evaluator.version
        );

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
        prompt_ref: {
          name: data.promptVersions[0].promptName,
          version_list: data.promptVersions.map(pv => pv.version),
          variable_mapping: promptVariableMapping,
        },
        eval_list: evalList,
      });
      handleCloseModal();
      return { id: result.id };
    } catch (err) {
      console.error("Failed to create experiment:", err);
      throw err;
    }
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
              <Chip label={getStatusLabel(experiment.status)} color={getStatusColor(experiment.status)} size="small" />
            </Box>
            <Button
              variant="outlined"
              startIcon={<ContentCopyIcon />}
              onClick={handleCreateFromExisting}
            >
              Create from Existing
            </Button>
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
              <span className="font-medium">Prompt:</span> {experiment.prompt_name}
            </Box>
            {experiment.total_cost && (
              <Box>
                <span className="font-medium">Total Cost:</span> {formatCurrency(parseFloat(experiment.total_cost))}
              </Box>
            )}
          </Box>
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
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-4">
              {experiment.summary_results.prompt_eval_summaries.map((promptSummary) => (
                <Card key={`${promptSummary.prompt_name}-${promptSummary.prompt_version}`} elevation={1}>
                  <CardContent>
                    <Box className="flex items-center gap-2 mb-3">
                      <Typography variant="subtitle1" className="font-medium text-gray-800 truncate flex-1 min-w-0">
                        Prompt: {promptSummary.prompt_name}
                      </Typography>
                      <Chip label={`v${promptSummary.prompt_version}`} size="small" color="primary" className="flex-shrink-0" />
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
                  </CardContent>
                </Card>
              ))}
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
              title="This table shows individual test case results. Each row represents one test case from your dataset, showing evaluation failures across all prompt versions and the total cost."
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
          {taskId && experimentId && <ExperimentResultsTable taskId={taskId} experimentId={experimentId} />}
        </Box>
      </Box>

      {/* Create from Existing Modal */}
      <CreateExperimentModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onSubmit={handleSubmitExperiment}
        initialData={experiment}
      />
    </Box>
  );
};
