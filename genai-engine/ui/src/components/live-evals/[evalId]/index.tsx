import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import FilterListIcon from "@mui/icons-material/FilterList";
import { Box, Chip, CircularProgress, IconButton, Paper, Stack, Typography } from "@mui/material";
import { Link, useParams } from "react-router-dom";

import { useContinuousEval } from "../hooks/useContinuousEval";

import { CopyableChip } from "@/components/common";
import { getContentHeight } from "@/constants/layout";
import { formatDate } from "@/utils/formatters";

export const LiveEvalDetail = () => {
  const { evalId } = useParams<{ evalId: string }>();

  // In real implementation, fetch data using evalId
  const { data: liveEval } = useContinuousEval(evalId ?? "");

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
        <Stack direction="row" alignItems="center" spacing={2} mb={1}>
          <IconButton component={Link} to=".." size="small" sx={{ mr: -1 }}>
            <ArrowBackIcon fontSize="small" />
          </IconButton>
          <Typography variant="h5" fontWeight="bold" color="text.primary">
            {liveEval.name}
          </Typography>
          {/* <LiveEvalStatusChip status={liveEval.status} /> */}
        </Stack>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Stack direction="row" spacing={3} alignItems="center">
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="body2" color="text.secondary">
                ID:
              </Typography>
              <CopyableChip label={evalId ?? liveEval.id} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Created {formatDate(liveEval.created_at)}
            </Typography>
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Stack spacing={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Evaluator
                </Typography>
                <Typography variant="body1" fontWeight={500}>
                  {liveEval.llm_eval_name}
                </Typography>
                <Chip label={`v${liveEval.llm_eval_version}`} size="small" sx={{ width: "fit-content" }} />
              </Stack>

              <Stack spacing={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Transform
                </Typography>
                <Typography variant="body1" fontWeight={500}>
                  {liveEval.transform_id}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Dataset: {liveEval.transform_id}
                </Typography>
              </Stack>

              <Stack spacing={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  Variable Mappings
                </Typography>
                {/* <Stack spacing={0.5}>
                  {Object.entries(liveEval.config.variables).map(([variable, mapping]) => (
                    <Stack key={variable} direction="row" spacing={0.5} alignItems="center">
                      <Chip label={variable} size="small" variant="outlined" sx={{ fontFamily: "monospace", fontSize: "0.7rem", height: 22 }} />
                      <Typography variant="caption" color="text.secondary">
                        →
                      </Typography>
                      <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
                        {mapping}
                      </Typography>
                    </Stack>
                  ))}
                </Stack> */}
              </Stack>

              <Stack spacing={0.5}>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }}>
                  <FilterListIcon sx={{ fontSize: 14, verticalAlign: "middle", mr: 0.5 }} />
                  Filter Criteria
                </Typography>
                {/* {liveEval.config.filter.spanTypes && (
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                    <Typography variant="caption" color="text.secondary">
                      Span types:
                    </Typography>
                    {liveEval.config.filter.spanTypes.map((type) => (
                      <Chip key={type} label={type} size="small" sx={{ height: 20, fontSize: "0.7rem" }} />
                    ))}
                  </Stack>
                )} */}
                {/* {liveEval.config.filter.metadata && (
                  <Stack spacing={0.25}>
                    {Object.entries(liveEval.config.filter.metadata).map(([key, value]) => (
                      <Typography key={key} variant="caption" sx={{ fontFamily: "monospace" }}>
                        {key}: {value}
                      </Typography>
                    ))}
                  </Stack>
                )} */}
              </Stack>
            </div>
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
                  <TableRow sx={{ backgroundColor: "grey.50" }}>
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
