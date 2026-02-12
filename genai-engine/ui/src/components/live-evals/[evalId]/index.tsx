import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import {
  Box,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  Paper,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { Link as MuiLink } from "@mui/material";
import { Link, useParams } from "react-router-dom";

import { useContinuousEval } from "../hooks/useContinuousEval";

import { CopyableChip } from "@/components/common";
import { getContentHeight } from "@/constants/layout";
import { useTransform } from "@/hooks/transforms/useTransform";
import { formatDate } from "@/utils/formatters";

export const LiveEvalDetail = () => {
  const { evalId } = useParams<{ evalId: string }>();

  // In real implementation, fetch data using evalId
  const { data: liveEval } = useContinuousEval(evalId ?? "");

  const transform = useTransform(liveEval?.transform_id);

  const hasVariableMappings = liveEval?.transform_variable_mapping && liveEval.transform_variable_mapping.length > 0;

  if (!liveEval) {
    return (
      <div className="flex items-center justify-center h-full">
        <CircularProgress />
      </div>
    );
  }

  return (
    <Stack sx={{ height: getContentHeight() }}>
      {/* Header */}
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack direction="row" alignItems="flex-start" gap={2}>
          <IconButton component={Link} to=".." size="small">
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Stack>
            <Stack direction="row" alignItems="center" gap={2}>
              <Typography variant="h5" fontWeight="bold" color="text.primary">
                {liveEval.name}
              </Typography>
              <Chip label={liveEval.enabled ? "Enabled" : "Disabled"} color={liveEval.enabled ? "success" : "default"} size="small" />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {liveEval.description}
            </Typography>
          </Stack>

          <Stack direction="row" alignItems="center" justifyContent="space-between" ml="auto">
            <Stack direction="row" gap={2} alignItems="center">
              <CopyableChip label={evalId ?? liveEval.id} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />
              <Typography variant="body2" color="text.secondary">
                Created {formatDate(liveEval.created_at)}
              </Typography>
            </Stack>
          </Stack>
        </Stack>
      </Box>

      {/* Content */}
      <Box sx={{ flex: 1, overflow: "auto", p: 3 }}>
        <Stack spacing={3}>
          {/* Stats Overview */}
          {/* <Stack direction="row" spacing={2} sx={{ flexWrap: "wrap" }} useFlexGap>
            <StatCard
              icon={<TimelineIcon />}
              label="Total Evaluated"
              value={liveEval.stats.totalEvaluated.toLocaleString()}
              subValue={`${liveEval.stats.evaluatedToday} today`}
            />
            <StatCard
              icon={<CheckCircleOutlineIcon />}
              label="Pass Rate"
              value={`${liveEval.stats.passRate}%`}
              subValue={`${liveEval.stats.passCount} passed`}
              color="success"
            />
            <StatCard
              icon={<RemoveCircleOutlineIcon />}
              label="Failed"
              value={liveEval.stats.failCount}
              subValue={`${liveEval.stats.errorCount} errors`}
              color={liveEval.stats.failCount > 0 ? "error" : "default"}
            />
            <StatCard
              icon={<SpeedIcon />}
              label="Avg Score"
              value={liveEval.stats.avgScore?.toFixed(2) ?? "-"}
              subValue={`~${liveEval.stats.avgLatencyMs}ms latency`}
            />
          </Stack> */}

          {/* Configuration Section */}
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Configuration
            </Typography>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Stack gap={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Evaluator
                </Typography>
                <Stack direction="row" alignItems="center" gap={1}>
                  <MuiLink
                    variant="body1"
                    fontWeight={500}
                    component={Link}
                    to={`/tasks/${liveEval.task_id}/evaluators/${liveEval.llm_eval_name}/versions/${liveEval.llm_eval_version}`}
                  >
                    {liveEval.llm_eval_name}
                  </MuiLink>
                  <Chip label={`v${liveEval.llm_eval_version}`} size="small" sx={{ width: "fit-content" }} />
                </Stack>
              </Stack>

              <Stack spacing={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Transform
                </Typography>
                {transform.isLoading ? (
                  <Skeleton variant="text" width={100} height={20} />
                ) : (
                  <MuiLink variant="body1" fontWeight={500} component={Link} to={`/tasks/${liveEval.task_id}/transforms?id=${transform.data?.id}`}>
                    {transform.data?.name}
                  </MuiLink>
                )}
              </Stack>
            </div>

            {/* Variable Mappings */}
            {hasVariableMappings && (
              <>
                <Divider sx={{ my: 3 }} />
                <Stack gap={2}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    Variable Mappings
                  </Typography>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.50") }}>
                        <TableCell sx={{ fontWeight: 600 }}>Eval Variable</TableCell>
                        <TableCell sx={{ width: 40 }} />
                        <TableCell sx={{ fontWeight: 600 }}>Transform Variable</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {liveEval.transform_variable_mapping?.map((mapping) => (
                        <TableRow key={mapping.eval_variable}>
                          <TableCell>
                            <Chip label={mapping.eval_variable} size="small" variant="outlined" sx={{ fontFamily: "monospace" }} />
                          </TableCell>
                          <TableCell sx={{ textAlign: "center" }}>
                            <ArrowForwardIcon fontSize="small" color="action" />
                          </TableCell>
                          <TableCell>
                            <Chip label={mapping.transform_variable} size="small" variant="outlined" sx={{ fontFamily: "monospace" }} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Stack>
              </>
            )}
          </Paper>

          {/* Evaluated Traces */}
          <Paper variant="outlined" sx={{ overflow: "hidden" }}>
            <Box sx={{ px: 3, py: 2, borderBottom: 1, borderColor: "divider" }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Stack>
                  <Typography variant="h6" fontWeight={600}>
                    Evaluated Traces
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Real-time evaluation results as traces are processed
                  </Typography>
                </Stack>
                {/* <Chip label={`${liveEval.evaluatedTraces.length} recent`} size="small" variant="outlined" /> */}
              </Stack>
            </Box>
            {/* <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ backgroundColor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.50") }}>
                    <TableCell sx={{ fontWeight: 600 }}>Trace</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Evaluated</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Result</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Reason</TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="right">
                      Latency
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600 }} align="right">
                      Tokens
                    </TableCell>
                    <TableCell sx={{ fontWeight: 600, width: 48 }} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {liveEval.evaluatedTraces.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((trace) => (
                    <TableRow key={trace.id} hover>
                      <TableCell>
                        <CopyableChip label={trace.traceId} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />
                      </TableCell>
                      <TableCell>
                        <Tooltip title={formatDate(trace.evaluatedAt)}>
                          <Typography variant="body2" color="text.secondary">
                            {formatRelativeTime(trace.evaluatedAt)}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <ResultChip result={trace.result} score={trace.score} />
                      </TableCell>
                      <TableCell sx={{ maxWidth: 300 }}>
                        <Tooltip title={trace.reason ?? ""}>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                              maxWidth: 280,
                            }}
                          >
                            {trace.reason ?? "-"}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" color="text.secondary">
                          {trace.latencyMs}ms
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title={`Input: ${trace.inputTokens} / Output: ${trace.outputTokens}`}>
                          <Typography variant="body2" color="text.secondary">
                            {trace.inputTokens + trace.outputTokens}
                          </Typography>
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        <Tooltip title="View trace">
                          <IconButton
                            size="small"
                            component={Link}
                            to={`/tasks/${task?.id}/traces${serializeDrawerTarget({ target: "trace", id: trace.traceId })}`}
                          >
                            <OpenInNewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer> */}
            {/* <TablePagination
              component="div"
              count={liveEval.evaluatedTraces.length}
              page={page}
              onPageChange={(_, newPage) => setPage(newPage)}
              rowsPerPage={rowsPerPage}
              onRowsPerPageChange={(e) => {
                setRowsPerPage(parseInt(e.target.value, 10));
                setPage(0);
              }}
              rowsPerPageOptions={[10, 25, 50]}
            /> */}
          </Paper>
        </Stack>
      </Box>
    </Stack>
  );
};
