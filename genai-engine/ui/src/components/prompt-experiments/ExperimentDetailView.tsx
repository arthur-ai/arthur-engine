import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import { Box, Typography, Chip, LinearProgress, Card, CardContent, Tooltip, Button } from "@mui/material";
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { CreateExperimentModal, ExperimentFormData } from "./CreateExperimentModal";
import { ExperimentResultsTable } from "./ExperimentResultsTable";
import { PromptVersionDrawer } from "./PromptVersionDrawer";

import { getContentHeight } from "@/constants/layout";
import { usePromptExperiment, useCreateExperiment } from "@/hooks/usePromptExperiments";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";
import { formatUTCTimestamp, formatTimestampDuration, formatCurrency } from "@/utils/formatters";

interface PromptVersionDetails {
  prompt_name: string;
  prompt_version: string;
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
  const { experiment, isLoading, error, refetch } = usePromptExperiment(experimentId);
  const createExperiment = useCreateExperiment(taskId);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptVersionDetails | null>(null);

  const handlePromptClick = (promptSummary: PromptVersionDetails) => {
    setSelectedPrompt(promptSummary);
    setDrawerOpen(true);
  };

  const handleDrawerClose = () => {
    setDrawerOpen(false);
  };

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
        prompt_ref: {
          name: data.promptVersions[0].promptName,
          version_list: data.promptVersions.map((pv) => pv.version),
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
            <Button variant="outlined" startIcon={<ContentCopyIcon />} onClick={handleCreateFromExisting}>
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
                  return parseInt(b.prompt_version) - parseInt(a.prompt_version);
                });

                // Find the max total passes to identify best performing prompts
                const maxTotalPasses =
                  sortedSummaries.length > 0
                    ? Math.max(...sortedSummaries.map((summary) => summary.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0)))
                    : 0;

                return sortedSummaries.map((promptSummary) => {
                  const totalPasses = promptSummary.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const isBestPerforming = totalPasses === maxTotalPasses;

                  return (
                    <Card
                      key={`${promptSummary.prompt_name}-${promptSummary.prompt_version}`}
                      elevation={1}
                      onClick={() => handlePromptClick(promptSummary)}
                      sx={{ cursor: "pointer", "&:hover": { boxShadow: 3 }, position: "relative" }}
                    >
                      <CardContent sx={{ position: "relative", paddingBottom: "16px !important" }}>
                        <Box className="flex items-center gap-2 mb-3">
                          <Typography variant="subtitle1" className="font-medium text-gray-800 truncate flex-1 min-w-0">
                            Prompt: {promptSummary.prompt_name} (v{promptSummary.prompt_version})
                          </Typography>
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
              promptSummaries={(() => {
                // Sort prompt summaries the same way as in Overall Prompt Performance
                const sorted = [...experiment.summary_results.prompt_eval_summaries].sort((a, b) => {
                  const totalPassesA = a.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const totalPassesB = b.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  if (totalPassesB !== totalPassesA) {
                    return totalPassesB - totalPassesA;
                  }
                  return parseInt(b.prompt_version) - parseInt(a.prompt_version);
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
        />
      )}
    </Box>
  );
};
