import AccessTimeIcon from "@mui/icons-material/AccessTime";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  LinearProgress,
  Paper,
  Typography,
} from "@mui/material";

import { CopyableChip } from "@/components/common";
import { useEval } from "@/components/evaluators/hooks/useEval";
import NunjucksHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { useAnnotation } from "@/components/live-evals/hooks/useAnnotation";
import { useRerunContinuousEval } from "@/components/live-evals/hooks/useRerunContinuousEval";
import { useTask } from "@/hooks/useTask";
import { formatDate } from "@/utils/formatters";

type Props = {
  annotationId?: string;
  onClose: () => void;
  onRerunComplete: () => void;
  rerunOnMount?: boolean;
};

export const Details = ({ annotationId, onClose, rerunOnMount = false, onRerunComplete }: Props) => {
  const { task } = useTask();

  const { data, isLoading } = useAnnotation(annotationId!);

  const rerunMutation = useRerunContinuousEval({ annotationId: annotationId!, rerunOnMount, onSuccess: onRerunComplete });

  const { eval: evalData, isLoading: isLoadingEval } = useEval(task?.id, data?.eval_name ?? undefined, data?.eval_version?.toString() ?? undefined);
  const instructions = evalData?.instructions;

  const getStatusChip = (status: string) => {
    const isPassed = status === "passed";
    return (
      <Chip
        icon={isPassed ? <CheckCircleIcon /> : <ErrorIcon />}
        label={status.toUpperCase()}
        color={isPassed ? "success" : "error"}
        size="small"
        sx={{ fontWeight: 600 }}
      />
    );
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "success.main";
    if (score >= 0.5) return "warning.main";
    return "error.main";
  };

  const isPending = data?.run_status === "pending";

  return (
    <>
      <DialogTitle>
        <Typography variant="h6" fontWeight={600}>
          Annotation Details
        </Typography>
      </DialogTitle>

      {isPending ? <LinearProgress /> : null}

      <DialogContent dividers>
        {isLoading ? (
          <Box className="flex items-center justify-center py-12">
            <CircularProgress />
          </Box>
        ) : data ? (
          <Box className="flex flex-col gap-4">
            {/* Error Alert with Rerun Action */}
            {data.run_status === "error" && (
              <Alert
                severity="error"
                action={
                  <Button
                    color="inherit"
                    size="small"
                    startIcon={<RestartAltIcon />}
                    onClick={() => rerunMutation.mutate(data.id)}
                    loading={rerunMutation.isPending}
                  >
                    Rerun
                  </Button>
                }
              >
                This evaluation failed. You can retry it.
              </Alert>
            )}

            {/* Status, Score, and Eval Name Section */}
            <Box className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {data.run_status && (
                <Paper variant="outlined" sx={{ p: 2, opacity: isPending ? 0.5 : 1 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    Status
                  </Typography>
                  {getStatusChip(data.run_status)}
                </Paper>
              )}

              {data.annotation_score != null && (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    Score
                  </Typography>
                  <Typography variant="h5" fontWeight={700} sx={{ color: getScoreColor(data.annotation_score) }}>
                    {data.annotation_score}
                  </Typography>
                </Paper>
              )}

              {data.eval_name && (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    Eval Name
                  </Typography>
                  <Box className="flex items-center gap-1">
                    <Chip label={data.eval_name} size="small" color="primary" variant="outlined" sx={{ fontWeight: 500 }} />
                    {data.eval_version != null && <Chip label={`v${data.eval_version}`} size="small" variant="outlined" sx={{ fontWeight: 500 }} />}
                  </Box>
                </Paper>
              )}
            </Box>

            {/* Explanation */}
            {data.annotation_description && (
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Explanation
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    backgroundColor: "action.hover",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                    {data.annotation_description}
                  </Typography>
                </Paper>
              </Box>
            )}

            {/* Eval Instructions */}
            {isLoadingEval ? (
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Evaluation Criteria
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, display: "flex", justifyContent: "center" }}>
                  <CircularProgress size={24} />
                </Paper>
              </Box>
            ) : instructions ? (
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Evaluation Criteria
                </Typography>
                <Box
                  sx={{
                    "& .MuiTextField-root": {
                      display: "flex",
                      flexDirection: "column",
                    },
                    "& .MuiInputBase-root": {
                      maxHeight: 300,
                      alignItems: "flex-start",
                    },
                    "& .MuiInputBase-input": {
                      overflow: "auto !important",
                    },
                  }}
                >
                  <NunjucksHighlightedTextField
                    value={instructions}
                    onChange={() => {}} // Read-only, no-op
                    disabled
                    multiline
                    minRows={4}
                    size="small"
                  />
                </Box>
              </Box>
            ) : null}

            <Divider />

            {/* Input Variables */}
            {data.input_variables && data.input_variables.length > 0 && (
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Input Variables ({data.input_variables.length})
                </Typography>
                <Box className="flex flex-col gap-2">
                  {data.input_variables.map((variable: { name: string; value: string }, idx: number) => (
                    <Paper
                      key={idx}
                      variant="outlined"
                      sx={{
                        p: 2,
                        backgroundColor: "action.hover",
                      }}
                    >
                      <Box className="flex items-center gap-2 mb-2">
                        <Chip label={variable.name} size="small" color="primary" variant="outlined" sx={{ fontWeight: 500 }} />
                      </Box>
                      <Box
                        component="pre"
                        sx={{
                          m: 0,
                          p: 1.5,
                          backgroundColor: "background.paper",
                          borderRadius: 1,
                          border: "1px solid",
                          borderColor: "divider",
                          fontSize: 12,
                          fontFamily: "monospace",
                          overflow: "auto",
                          maxHeight: 200,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {variable.value}
                      </Box>
                    </Paper>
                  ))}
                </Box>
              </Box>
            )}

            <Divider />

            {/* Stats Row */}
            <Box>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Metadata
              </Typography>
              <Box className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <Paper variant="outlined" sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
                  <AttachMoneyIcon color="action" />
                  <Box>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Cost
                    </Typography>
                    <Typography variant="body1" fontWeight={600}>
                      ${data.cost?.toFixed(6) ?? "N/A"}
                    </Typography>
                  </Box>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
                  <AccessTimeIcon color="action" />
                  <Box>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Created
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {data.created_at ? formatDate(data.created_at) : "N/A"}
                    </Typography>
                  </Box>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2, display: "flex", alignItems: "center", gap: 1.5 }}>
                  <AccessTimeIcon color="action" />
                  <Box>
                    <Typography variant="caption" color="text.secondary" display="block">
                      Updated
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {data.updated_at ? formatDate(data.updated_at) : "N/A"}
                    </Typography>
                  </Box>
                </Paper>

                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    Annotation Type
                  </Typography>
                  <Chip label={data.annotation_type} size="small" variant="outlined" sx={{ fontWeight: 500 }} />
                </Paper>
              </Box>
            </Box>

            <Divider />

            {/* IDs Section */}
            <Box>
              <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                IDs
              </Typography>
              <Box className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    Annotation ID
                  </Typography>
                  <CopyableChip label={data.id} sx={{ fontFamily: "monospace", fontSize: 12 }} />
                </Paper>

                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                    Trace ID
                  </Typography>
                  <CopyableChip label={data.trace_id} sx={{ fontFamily: "monospace", fontSize: 12 }} />
                </Paper>

                {data.continuous_eval_id && (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                      Continuous Eval ID
                    </Typography>
                    <CopyableChip label={data.continuous_eval_id} sx={{ fontFamily: "monospace", fontSize: 12 }} />
                  </Paper>
                )}
              </Box>
            </Box>
          </Box>
        ) : (
          <Typography color="text.secondary" className="text-center py-8">
            No annotation data available
          </Typography>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </>
  );
};
