import AccessTimeIcon from "@mui/icons-material/AccessTime";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import { Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Paper, Typography } from "@mui/material";

import { CopyableChip } from "@/components/common";
import { useAnnotation } from "@/components/live-evals/hooks/useAnnotation";
import { formatDate } from "@/utils/formatters";

type Props = {
  annotationId?: string;
  onClose: () => void;
};

export const Details = ({ annotationId, onClose }: Props) => {
  const { data, isLoading } = useAnnotation(annotationId);

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

  return (
    <Dialog open={!!annotationId} onClose={onClose} maxWidth="xl" fullWidth>
      <DialogTitle className="flex items-center justify-between gap-4">
        <Box className="flex items-center gap-3">
          <Typography variant="h6" fontWeight={600}>
            Annotation Details
          </Typography>
          {data?.run_status && getStatusChip(data.run_status)}
        </Box>
        {data?.annotation_score != null && (
          <Box className="flex items-center gap-2">
            <Typography variant="body2" color="text.secondary">
              Score
            </Typography>
            <Typography variant="h5" fontWeight={700} sx={{ color: getScoreColor(data.annotation_score) }}>
              {data.annotation_score}
            </Typography>
          </Box>
        )}
      </DialogTitle>

      <DialogContent dividers>
        {isLoading ? (
          <Box className="flex items-center justify-center py-12">
            <CircularProgress />
          </Box>
        ) : data ? (
          <Box className="flex flex-col gap-4">
            {/* IDs Section */}
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

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                  Annotation Type
                </Typography>
                <Chip label={data.annotation_type} size="small" variant="outlined" sx={{ fontWeight: 500 }} />
              </Paper>
            </Box>

            {/* Stats Row */}
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
            </Box>

            <Divider />

            {/* Description */}
            {data.annotation_description && (
              <Box>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Description
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                  }}
                >
                  <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
                    {data.annotation_description}
                  </Typography>
                </Paper>
              </Box>
            )}

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
                        backgroundColor: "grey.50",
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
                          backgroundColor: "white",
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
    </Dialog>
  );
};
