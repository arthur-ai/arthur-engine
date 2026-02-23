import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import { alpha } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import { useNavigate } from "react-router-dom";

import { useTask } from "@/hooks/useTask";
import type {
  PromptExperimentDetail,
  PromptExperimentSummary,
  PromptVariableMappingOutput,
  EvalRefOutput,
  EvalVariableMappingOutput,
  PromptEvalResultSummaries,
  EvalResultSummary,
} from "@/lib/api-client/api-client";

export interface ExperimentConfigDrawerProps {
  open: boolean;
  onClose: () => void;
  experimentConfig: Partial<PromptExperimentDetail>;
  notebookId: string | null;
  runs: PromptExperimentSummary[];
  expandedRunId: string | null;
  runDetails: Map<string, PromptExperimentDetail>;
  onExpandRun: (runId: string) => void;
}

/**
 * Right-side drawer that displays the active experiment configuration:
 * experiment name, dataset, prompt/eval variable mappings, and run history.
 */
export default function ExperimentConfigDrawer({
  open,
  onClose,
  experimentConfig,
  notebookId,
  runs,
  expandedRunId,
  runDetails,
  onExpandRun,
}: ExperimentConfigDrawerProps) {
  const navigate = useNavigate();
  const { task } = useTask();

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
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
        <Box sx={{ p: 2, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="h6">Experiment Configuration</Typography>
          <IconButton onClick={onClose} size="small">
            <ChevronLeftIcon />
          </IconButton>
        </Box>

        <Box sx={{ flex: 1, overflowY: "auto", p: 3 }}>
          {experimentConfig ? (
            <Stack spacing={3}>
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
                            backgroundColor: (theme) => (theme.palette.mode === "dark" ? alpha(theme.palette.primary.main, 0.12) : "primary.50"),
                            borderLeft: "3px solid",
                            borderLeftColor: "primary.main",
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
                            <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "primary.dark" }}>
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
                                      theme.palette.mode === "dark"
                                        ? isDatasetColumn
                                          ? alpha(theme.palette.primary.main, 0.12)
                                          : alpha(theme.palette.warning.main, 0.12)
                                        : isDatasetColumn
                                          ? "primary.50"
                                          : "warning.50",
                                    borderLeft: "3px solid",
                                    borderLeftColor: isDatasetColumn ? "primary.main" : "warning.main",
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
                                        <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "primary.dark" }}>
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
                                            <Box component="span" sx={{ fontFamily: "monospace", fontWeight: 600, color: "warning.dark" }}>
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

              {runs.length > 0 && (
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: "text.secondary" }}>
                    EXPERIMENT HISTORY ({runs.length})
                  </Typography>
                  <Stack spacing={1}>
                    {runs.map((run: PromptExperimentSummary, idx: number) => {
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
                              theme.palette.mode === "dark"
                                ? isCompleted
                                  ? alpha(theme.palette.success.main, 0.08)
                                  : isFailed
                                    ? alpha(theme.palette.error.main, 0.08)
                                    : "background.paper"
                                : isCompleted
                                  ? "success.50"
                                  : isFailed
                                    ? "error.50"
                                    : "background.paper",
                          }}
                        >
                          <Box
                            onClick={() => onExpandRun(run.id)}
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
                                  backgroundColor: isCompleted
                                    ? "success.main"
                                    : isFailed
                                      ? "error.main"
                                      : isRunning
                                        ? "warning.main"
                                        : "text.secondary",
                                  color: "common.white",
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

                          {isExpanded && details?.summary_results?.prompt_eval_summaries && (
                            <Box
                              sx={{
                                borderTop: "1px solid",
                                borderColor: "divider",
                                px: 1.5,
                                py: 1.5,
                                backgroundColor: (theme) =>
                                  theme.palette.mode === "dark" ? alpha(theme.palette.common.white, 0.02) : alpha(theme.palette.common.black, 0.02),
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
                                        const percentage = evalResult.total_count > 0 ? (evalResult.pass_count / evalResult.total_count) * 100 : 0;
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
  );
}
