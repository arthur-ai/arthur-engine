import { Box, Typography, Chip, LinearProgress, Card, CardContent, IconButton } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getContentHeight } from "@/constants/layout";
import { ExperimentResultsTable } from "./ExperimentResultsTable";
import { usePromptExperiment } from "@/hooks/usePromptExperiments";
import type { PromptExperimentDetail } from "@/lib/api-client/api-client";
import { formatUTCTimestamp } from "@/utils/formatters";

export const ExperimentDetailView: React.FC = () => {
  const { id: taskId, experimentId } = useParams<{ id: string; experimentId: string }>();
  const navigate = useNavigate();
  const { experiment, isLoading, error } = usePromptExperiment(experimentId);

  const getStatusColor = (status: PromptExperimentDetail["status"]): "default" | "primary" | "info" | "success" | "error" => {
    switch (status) {
      case "queued":
        return "default";
      case "running":
        return "primary";
      case "evaluating":
        return "info";
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
    <Box
      className="w-full overflow-auto"
      style={{ height: getContentHeight() }}
    >
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
          <Box className="flex items-center gap-3 mb-2">
            <Typography variant="h4" className="font-semibold text-gray-900">
              {experiment.name}
            </Typography>
            <Chip
              label={getStatusLabel(experiment.status)}
              color={getStatusColor(experiment.status)}
              size="small"
            />
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
            <Box>
              <span className="font-medium">Prompt:</span> {experiment.prompt_name}
            </Box>
          </Box>
        </Box>

        {/* Overall Performance Section */}
        <Box className="mb-6">
          <Typography variant="h5" className="font-semibold mb-4 text-gray-900">
            Overall Performance
          </Typography>

          {experiment.summary_results.prompt_eval_summaries.length === 0 ? (
            <Box className="p-6 bg-gray-50 border border-gray-200 rounded">
              <Typography variant="body1" className="text-gray-600 italic">
                Overall performance will be shown when the experiment finishes executing test cases.
              </Typography>
            </Box>
          ) : (
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 2xl:grid-cols-8 gap-4">
              {experiment.summary_results.prompt_eval_summaries.map((promptSummary) => (
                <React.Fragment key={`${promptSummary.prompt_name}-${promptSummary.prompt_version}`}>
                  {/* Version Tile */}
                  <Card elevation={1}>
                    <CardContent>
                      <Typography variant="subtitle1" className="font-medium mb-1 text-gray-800">
                        Prompt: {promptSummary.prompt_name}
                      </Typography>
                      <Typography variant="h4" className="font-bold text-gray-900">
                        v{promptSummary.prompt_version}
                      </Typography>
                    </CardContent>
                  </Card>

                  {/* Eval Result Tiles */}
                  {promptSummary.eval_results.map((evalResult) => {
                    const percentage = (evalResult.pass_count / evalResult.total_count) * 100;
                    const isGood = percentage >= 80;
                    const isMedium = percentage >= 60 && percentage < 80;

                    return (
                      <Card key={`${evalResult.eval_name}-${evalResult.eval_version}`} elevation={1}>
                        <CardContent>
                          <Typography variant="subtitle1" className="font-medium mb-3 text-gray-800">
                            Prompt: {evalResult.eval_name} v{evalResult.eval_version}
                          </Typography>

                          <Box className="space-y-2">
                            <Box className="flex justify-between items-center mb-1">
                              <Typography variant="caption" className="font-medium text-gray-700">
                                Pass Rate
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
                                backgroundColor: "#e5e7eb",
                                "& .MuiLinearProgress-bar": {
                                  backgroundColor: isGood ? "#10b981" : isMedium ? "#f59e0b" : "#ef4444",
                                },
                              }}
                            />
                            <Typography variant="caption" className="text-gray-500 text-xs">
                              {evalResult.pass_count} / {evalResult.total_count}
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    );
                  })}
                </React.Fragment>
              ))}
            </Box>
          )}
        </Box>

        {/* Detailed Results Section */}
        <Box className="mb-6">
          <Typography variant="h5" className="font-semibold mb-4 text-gray-900">
            Detailed Results
          </Typography>
          {taskId && experimentId && (
            <ExperimentResultsTable
              taskId={taskId}
              experimentId={experimentId}
            />
          )}
        </Box>
      </Box>
    </Box>
  );
};
