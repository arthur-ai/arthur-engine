import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DeleteIcon from "@mui/icons-material/Delete";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LaunchIcon from "@mui/icons-material/Launch";
import {
  Box,
  Typography,
  Chip,
  LinearProgress,
  Card,
  CardContent,
  Tooltip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Link,
} from "@mui/material";
import React, { useState } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";

import { RagExperimentTestCasesTable } from "./RagExperimentTestCasesTable";
import { formatRagConfigName, getRagConfigDisplayName } from "./utils";

import { getContentHeight } from "@/constants/layout";
import { useRagExperimentWithPolling, useDeleteRagExperiment } from "@/hooks/useRagExperiments";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { formatDateInTimezone, formatTimestampDuration, capitalize } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

export const RagExperimentDetailView: React.FC = () => {
  const { id: taskId, experimentId } = useParams<{ id: string; experimentId: string }>();
  const navigate = useNavigate();
  const { timezone, use24Hour } = useDisplaySettings();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const { experiment, isLoading, error } = useRagExperimentWithPolling(experimentId);
  const deleteExperiment = useDeleteRagExperiment();

  const handleDeleteClick = () => {
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteCancel = () => {
    setIsDeleteDialogOpen(false);
  };

  const handleDeleteConfirm = async () => {
    if (!experimentId) return;

    try {
      await deleteExperiment.mutateAsync(experimentId);
      setIsDeleteDialogOpen(false);
      navigate(`/tasks/${taskId}/rag-experiments`);
    } catch {
      // Error handling is done by the mutation's error state
    }
  };

  const handleOpenInNotebook = () => {
    if (experiment?.notebook_id) {
      navigate(`/tasks/${taskId}/rag-notebooks/${experiment.notebook_id}`);
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
        <Box className="mb-4">
          <Box
            className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 cursor-pointer w-fit"
            onClick={() => navigate(`/tasks/${taskId}/rag-experiments`)}
          >
            <ArrowBackIcon fontSize="small" />
            <Typography variant="body2" className="font-medium">
              Back to RAG Experiments
            </Typography>
          </Box>
        </Box>

        <Box className="mb-6">
          <Box className="flex items-center justify-between mb-2">
            <Box className="flex items-center gap-3">
              <Typography variant="h4" className="font-semibold text-gray-900 dark:text-gray-100">
                {experiment.name}
              </Typography>
              <Chip label={capitalize(experiment.status)} size="small" sx={getStatusChipSx(experiment.status)} />
            </Box>
            <Box className="flex items-center gap-2">
              {experiment.notebook_id && (
                <Button variant="outlined" startIcon={<LaunchIcon />} onClick={handleOpenInNotebook}>
                  Open in Notebook
                </Button>
              )}
              <Button variant="outlined" color="error" startIcon={<DeleteIcon />} onClick={handleDeleteClick}>
                Delete
              </Button>
            </Box>
          </Box>
          {experiment.description && (
            <Typography variant="body1" className="text-gray-600 dark:text-gray-400 mb-4">
              {experiment.description}
            </Typography>
          )}
          <Box className="flex gap-6 text-sm text-gray-600 dark:text-gray-400">
            <Box>
              <span className="font-medium">Created:</span> {formatDateInTimezone(experiment.created_at, timezone, { hour12: !use24Hour })}
            </Box>
            <Box>
              <span className="font-medium">Finished:</span> {formatDateInTimezone(experiment.finished_at, timezone, { hour12: !use24Hour })}
            </Box>
            {experiment.finished_at && (
              <Box>
                <span className="font-medium">Duration:</span> {formatTimestampDuration(experiment.created_at, experiment.finished_at) || "-"}
              </Box>
            )}
            <Box>
              <span className="font-medium">RAG Configs:</span> {experiment.rag_configs.length} config
              {experiment.rag_configs.length > 1 ? "s" : ""}
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
            <Box>
              <span className="font-medium">Test Cases:</span> {experiment.completed_rows}/{experiment.total_rows}
            </Box>
          </Box>

          {experiment.dataset_row_filter && experiment.dataset_row_filter.length > 0 && (
            <Box className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded">
              <Box className="flex items-center gap-2 mb-2">
                <Typography variant="body2" className="font-medium text-gray-900 dark:text-gray-100">
                  Dataset Row Filter Applied
                </Typography>
                <Tooltip title="This experiment only includes dataset rows that match ALL of the following conditions." arrow placement="right">
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
                      backgroundColor: "background.paper",
                      borderColor: "primary.main",
                      color: "primary.dark",
                    }}
                  />
                ))}
              </Box>
            </Box>
          )}
        </Box>

        <Box className="mb-6">
          <Box className="flex items-center gap-2 mb-4">
            <Typography variant="h5" className="font-semibold text-gray-900 dark:text-gray-100">
              RAG Configurations
            </Typography>
            <Tooltip title="These are the RAG configurations being tested in this experiment." arrow placement="right">
              <InfoOutlinedIcon
                sx={{
                  fontSize: 20,
                  color: "text.secondary",
                  cursor: "help",
                }}
              />
            </Tooltip>
          </Box>
          <Box className="flex flex-wrap gap-2">
            {experiment.rag_configs.map((config, idx) => (
              <Chip
                key={idx}
                label={formatRagConfigName(config)}
                variant="outlined"
                sx={{
                  backgroundColor: config.type === "saved" ? "primary.50" : "warning.50",
                  borderColor: config.type === "saved" ? "primary.200" : "warning.200",
                }}
              />
            ))}
          </Box>
        </Box>

        <Box className="mb-6">
          <Box className="flex items-center gap-2 mb-4">
            <Typography variant="h5" className="font-semibold text-gray-900 dark:text-gray-100">
              Overall RAG Config Performance
            </Typography>
            <Tooltip
              title="Each tile shows the evaluation results for a specific RAG configuration. The progress bars indicate how many test cases passed for each evaluator."
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

          {experiment.summary_results.rag_eval_summaries.length === 0 ? (
            <Box className="p-6 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded">
              <Typography variant="body1" className="text-gray-600 dark:text-gray-400 italic">
                Overall performance will be shown when the experiment finishes executing test cases.
              </Typography>
            </Box>
          ) : (
            <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-4 gap-4">
              {(() => {
                const sortedSummaries = [...experiment.summary_results.rag_eval_summaries].sort((a, b) => {
                  const totalPassesA = a.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const totalPassesB = b.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);

                  if (totalPassesB !== totalPassesA) {
                    return totalPassesB - totalPassesA;
                  }

                  return (b.setting_configuration_version || 0) - (a.setting_configuration_version || 0);
                });

                const maxTotalPasses =
                  sortedSummaries.length > 0
                    ? Math.max(...sortedSummaries.map((summary) => summary.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0)))
                    : 0;

                return sortedSummaries.map((ragSummary, idx) => {
                  const totalPasses = ragSummary.eval_results.reduce((sum, evalResult) => sum + evalResult.pass_count, 0);
                  const isBestPerforming = totalPasses === maxTotalPasses && maxTotalPasses > 0;
                  const displayName = getRagConfigDisplayName(ragSummary, experiment.rag_configs);

                  return (
                    <Card key={ragSummary.rag_config_key || idx} elevation={1} sx={{ position: "relative" }}>
                      <CardContent sx={{ position: "relative", paddingBottom: "16px !important", minHeight: "180px" }}>
                        <Box className="flex items-center gap-2 mb-3">
                          <Typography variant="subtitle1" className="font-medium text-gray-800 dark:text-gray-200 truncate flex-1 min-w-0">
                            {displayName}
                          </Typography>
                          {ragSummary.rag_config_type === "unsaved" && (
                            <Chip
                              label="Unsaved"
                              size="small"
                              sx={{
                                backgroundColor: (theme) => (theme.palette.mode === "dark" ? "rgba(255,152,0,0.12)" : "#fff3e0"),
                                color: (theme) => (theme.palette.mode === "dark" ? "#ffb74d" : "#f57c00"),
                                fontWeight: 600,
                              }}
                              className="shrink-0"
                            />
                          )}
                          {isBestPerforming && <Chip label="Best" size="small" color="success" sx={{ fontWeight: 600 }} className="shrink-0" />}
                        </Box>

                        <Box className="space-y-3">
                          {ragSummary.eval_results.map((evalResult) => {
                            const percentage = evalResult.total_count > 0 ? (evalResult.pass_count / evalResult.total_count) * 100 : 0;

                            return (
                              <Box key={`${evalResult.eval_name}-${evalResult.eval_version}`}>
                                <Box className="flex justify-between items-center mb-1">
                                  <Typography variant="caption" className="font-medium text-gray-700 dark:text-gray-300">
                                    {evalResult.eval_name} (v{evalResult.eval_version})
                                  </Typography>
                                  <Typography variant="caption" className="text-gray-600 dark:text-gray-400">
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
                                <Typography variant="caption" className="text-gray-500 dark:text-gray-400 text-xs">
                                  {evalResult.pass_count} / {evalResult.total_count} test cases passed
                                </Typography>
                              </Box>
                            );
                          })}
                        </Box>
                      </CardContent>
                    </Card>
                  );
                });
              })()}
            </Box>
          )}
        </Box>

        {experiment.eval_list && experiment.eval_list.length > 0 && (
          <Box className="mb-6">
            <Box className="flex items-center gap-2 mb-4">
              <Typography variant="h5" className="font-semibold text-gray-900 dark:text-gray-100">
                Evaluators
              </Typography>
              <Tooltip title="These evaluators are being used to assess the RAG configurations." arrow placement="right">
                <InfoOutlinedIcon
                  sx={{
                    fontSize: 20,
                    color: "text.secondary",
                    cursor: "help",
                  }}
                />
              </Tooltip>
            </Box>
            <Box className="flex flex-wrap gap-2">
              {experiment.eval_list.map((evalRef, idx) => (
                <Chip
                  key={idx}
                  label={`${evalRef.name} (v${evalRef.version})`}
                  variant="outlined"
                  sx={{
                    backgroundColor: "info.50",
                    borderColor: "info.200",
                  }}
                />
              ))}
            </Box>
          </Box>
        )}

        <Box className="mb-6">
          <Box className="flex items-center gap-2 mb-4">
            <Typography variant="h5" className="font-semibold text-gray-900 dark:text-gray-100">
              Test Case Results
            </Typography>
            <Tooltip
              title="This table shows individual test case results. Each row represents one test case from your dataset, showing pass/fail for each RAG configuration and evaluator combination. Click a row to see detailed results including retrieved documents and evaluation explanations."
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
          {experimentId && (
            <RagExperimentTestCasesTable
              experimentId={experimentId}
              experimentStatus={experiment.status}
              ragConfigs={experiment.rag_configs}
              ragEvalSummaries={experiment.summary_results.rag_eval_summaries}
              datasetId={experiment.dataset_ref.id}
              datasetVersion={experiment.dataset_ref.version}
            />
          )}
        </Box>
      </Box>

      <Dialog open={isDeleteDialogOpen} onClose={handleDeleteCancel}>
        <DialogTitle>Delete RAG Experiment</DialogTitle>
        <DialogContent>
          <DialogContentText>Are you sure you want to delete the experiment "{experiment?.name}"? This action cannot be undone.</DialogContentText>
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
