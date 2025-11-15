import { Box, Typography, Chip, LinearProgress, Card, CardContent, IconButton } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useApi } from "@/hooks/useApi";
import { getContentHeight } from "@/constants/layout";
import { ExperimentResultsTable } from "./ExperimentResultsTable";

interface ExperimentDetail {
  id: string;
  name: string;
  description: string;
  created_at: string;
  finished_at: string;
  status: "queued" | "running" | "evaluating" | "failed" | "completed";
  prompt_name: string;
  dataset_ref: {
    id: string;
    version: string;
  };
  prompt_ref: {
    name: string;
    version_list: number[];
    variable_mapping: Array<{
      variable_name: string;
      source: {
        type: string;
        dataset_column?: {
          name: string;
        };
      };
    }>;
  };
  eval_list: Array<{
    name: string;
    version: string;
    variable_mapping: Array<{
      variable_name: string;
      source: {
        type: string;
        dataset_column?: {
          name: string;
        };
        experiment_output?: {
          json_path?: string;
        };
      };
    }>;
  }>;
  summary_results: {
    prompt_eval_summaries: Array<{
      prompt_name: string;
      prompt_version: number;
      eval_results: Array<{
        eval_name: string;
        eval_version: string;
        pass_count: number;
        total_count: number;
      }>;
    }>;
  };
}

export const ExperimentDetailView: React.FC = () => {
  const { id: taskId, experimentId } = useParams<{ id: string; experimentId: string }>();
  const navigate = useNavigate();
  const api = useApi();
  const [experiment, setExperiment] = useState<ExperimentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadExperiment();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId, experimentId, api]);

  const loadExperiment = async () => {
    if (!experimentId || !api) return;

    try {
      setLoading(true);
      setError(null);
      const response = await api.api.getPromptExperimentApiV1PromptExperimentsExperimentIdGet(experimentId);
      setExperiment(response.data as any);
    } catch (err) {
      console.error("Failed to load experiment:", err);
      setError("Failed to load experiment details");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return dateString;
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return dateString;
    }
  };

  const getStatusColor = (status: ExperimentDetail["status"]): "default" | "primary" | "info" | "success" | "error" => {
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

  const getStatusLabel = (status: ExperimentDetail["status"]): string => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  if (loading) {
    return (
      <Box className="flex items-center justify-center h-full">
        <Typography>Loading experiment...</Typography>
      </Box>
    );
  }

  if (error || !experiment) {
    return (
      <Box className="flex items-center justify-center h-full">
        <Typography color="error">{error || "Experiment not found"}</Typography>
      </Box>
    );
  }

  return (
    <Box
      className="w-full overflow-auto"
      style={{ height: getContentHeight() }}
    >
      <Box className="p-6 max-w-7xl mx-auto">
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
              <span className="font-medium">Created:</span> {formatDate(experiment.created_at)}
            </Box>
            <Box>
              <span className="font-medium">Finished:</span> {formatDate(experiment.finished_at)}
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

          <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {experiment.summary_results.prompt_eval_summaries.map((promptSummary) => (
              <Card key={`${promptSummary.prompt_name}-${promptSummary.prompt_version}`} elevation={1}>
                <CardContent>
                  <Typography variant="subtitle1" className="font-medium mb-3 text-gray-800">
                    {promptSummary.prompt_name} v{promptSummary.prompt_version}
                  </Typography>

                  <Box className="space-y-3">
                    {promptSummary.eval_results.map((evalResult) => {
                      const percentage = (evalResult.pass_count / evalResult.total_count) * 100;
                      const isGood = percentage >= 80;
                      const isMedium = percentage >= 60 && percentage < 80;

                      return (
                        <Box key={`${evalResult.eval_name}-${evalResult.eval_version}`}>
                          <Box className="flex justify-between items-center mb-1">
                            <Typography variant="caption" className="font-medium text-gray-700">
                              {evalResult.eval_name} v{evalResult.eval_version}
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
                      );
                    })}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
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
