import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  LinearProgress,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { createMRTColumnHelper, MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { useCreateTestRun, useTestRun, useTestRunResults } from "../hooks/useTestRun";

import { CopyableChip } from "@/components/common";
import { Details } from "@/components/live-evals/components/results/components/details";
import { serializeDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { AgenticAnnotationResponse } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

const MAX_TRACES = 50;

const columnHelper = createMRTColumnHelper<AgenticAnnotationResponse>();

type Props = {
  open: boolean;
  onClose: () => void;
  evalId: string;
  evalName: string;
  taskId: string;
  initialTraceIds?: string[];
};

function parseTraceIds(raw: string): string[] {
  return raw
    .split(/[\n,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export const TestRunDialog = ({ open, onClose, evalId, evalName, taskId, initialTraceIds }: Props) => {
  const { defaultCurrency } = useDisplaySettings();

  // Setup phase state
  const [traceIdsInput, setTraceIdsInput] = useState("");
  const [testRunId, setTestRunId] = useState<string | undefined>();
  const [selectedAnnotationId, setSelectedAnnotationId] = useState("");
  const autoStarted = useRef(false);
  const [retryCount, setRetryCount] = useState(0);

  const createMutation = useCreateTestRun(evalId);
  const testRunQuery = useTestRun(testRunId);
  const testRun = testRunQuery.data;
  const isRunning = testRun?.status === "running";
  const resultsQuery = useTestRunResults(testRunId);

  const parsedIds = useMemo(() => parseTraceIds(traceIdsInput), [traceIdsInput]);
  const tooMany = parsedIds.length > MAX_TRACES;
  const isEmpty = parsedIds.length === 0;

  // Auto-start when initialTraceIds are provided
  useEffect(() => {
    if (open && initialTraceIds && initialTraceIds.length > 0 && !testRunId && !autoStarted.current) {
      autoStarted.current = true;
      const unique = [...new Set(initialTraceIds)].slice(0, MAX_TRACES);
      createMutation
        .mutateAsync(unique)
        .then((result) => {
          setTestRunId(result.id);
        })
        .catch(() => {
          autoStarted.current = false;
        });
    }
  }, [open, initialTraceIds, retryCount]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRun = useCallback(async () => {
    const unique = [...new Set(parsedIds)];
    const result = await createMutation.mutateAsync(unique);
    setTestRunId(result.id);
  }, [parsedIds, createMutation]);

  const handleClose = () => {
    setTraceIdsInput("");
    setTestRunId(undefined);
    setSelectedAnnotationId("");
    setRetryCount(0);
    autoStarted.current = false;
    onClose();
  };

  const progress = testRun ? (testRun.total_count > 0 ? (testRun.completed_count / testRun.total_count) * 100 : 0) : 0;

  const columns = useMemo(
    () => [
      columnHelper.accessor("trace_id", {
        header: "Trace ID",
        Cell: ({ cell }) => <CopyableChip label={cell.getValue()} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />,
      }),
      columnHelper.accessor("run_status", {
        header: "Status",
        Cell: ({ cell }) => {
          const status = cell.getValue();
          return status ? (
            <Chip label={status} size="small" variant="outlined" sx={getStatusChipSx(status)} />
          ) : (
            <Typography variant="body2">—</Typography>
          );
        },
      }),
      columnHelper.accessor("annotation_score", {
        header: "Score",
        Cell: ({ cell }) => {
          const score = cell.getValue();
          return <Typography variant="body2">{score != null ? score : "—"}</Typography>;
        },
      }),
      columnHelper.accessor("annotation_description", {
        header: "Reason",
        size: 300,
        Cell: ({ cell }) => {
          const desc = cell.getValue();
          return (
            <Typography variant="body2" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 280 }}>
              {desc || "—"}
            </Typography>
          );
        },
      }),
      columnHelper.accessor("cost", {
        header: "Cost",
        Cell: ({ cell }) => {
          const cost = cell.getValue();
          return <Typography variant="body2">{cost != null ? formatCurrency(cost, defaultCurrency) : "—"}</Typography>;
        },
      }),
      columnHelper.display({
        id: "view_trace",
        header: "",
        size: 48,
        Cell: ({ row }) => (
          <Tooltip title="View trace">
            <IconButton
              size="small"
              component={Link}
              to={`/tasks/${taskId}/traces${serializeDrawerTarget({ target: "trace", id: row.original.trace_id })}`}
              onClick={(e: React.MouseEvent) => e.stopPropagation()}
            >
              <OpenInNewIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ),
      }),
    ],
    [taskId, defaultCurrency]
  );

  const resultsData = resultsQuery.data?.annotations ?? [];

  const table = useMaterialReactTable({
    columns,
    data: resultsData,
    enableTopToolbar: false,
    enableColumnActions: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableSorting: false,
    enablePagination: false,
    muiTablePaperProps: { elevation: 0, sx: { border: "none" } },
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => setSelectedAnnotationId(row.original.id),
      sx: { cursor: "pointer" },
    }),
  });

  const isSetupPhase = !testRunId && !initialTraceIds;

  return (
    <>
      <Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth>
        <DialogTitle>Test: {evalName}</DialogTitle>
        <DialogContent>
          {initialTraceIds && !testRunId ? (
            <Stack spacing={2} sx={{ mt: 1 }} alignItems="center" justifyContent="center" minHeight={120}>
              {createMutation.isError ? (
                <>
                  <Alert severity="error" sx={{ width: "100%" }}>
                    Failed to start test run. Please try again.
                  </Alert>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      autoStarted.current = false;
                      createMutation.reset();
                      setRetryCount((c) => c + 1);
                    }}
                  >
                    Retry
                  </Button>
                </>
              ) : (
                <>
                  <LinearProgress sx={{ width: "100%", borderRadius: 1, height: 6 }} />
                  <Typography variant="body2" color="text.secondary">
                    Starting test run with {Math.min(initialTraceIds.length, MAX_TRACES)} trace
                    {initialTraceIds.length !== 1 ? "s" : ""}...
                  </Typography>
                </>
              )}
            </Stack>
          ) : isSetupPhase ? (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                Paste trace IDs to test this eval against. Results are stored separately and won't affect production annotations.
              </Typography>
              <TextField
                multiline
                minRows={4}
                maxRows={12}
                variant="filled"
                label="Trace IDs"
                placeholder="Paste trace IDs, one per line or comma-separated"
                value={traceIdsInput}
                onChange={(e) => setTraceIdsInput(e.target.value)}
                error={tooMany}
                helperText={
                  tooMany
                    ? `Maximum ${MAX_TRACES} traces allowed`
                    : `${parsedIds.length} trace${parsedIds.length !== 1 ? "s" : ""} (max ${MAX_TRACES})`
                }
              />
            </Stack>
          ) : (
            <Stack spacing={2} sx={{ mt: 1 }}>
              {/* Progress */}
              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {testRun ? `${testRun.completed_count} / ${testRun.total_count} completed` : "Starting..."}
                  </Typography>
                  {testRun && !isRunning && (
                    <Typography variant="body2" fontWeight={600}>
                      {testRun.status === "completed" ? "Completed" : "Completed with issues"}
                    </Typography>
                  )}
                </Stack>
                <LinearProgress variant="determinate" value={progress} sx={{ borderRadius: 1, height: 6 }} />
              </Box>

              {/* Summary chips */}
              {testRun && (
                <Stack direction="row" gap={1} flexWrap="wrap">
                  {testRun.passed_count > 0 && <Chip label={`${testRun.passed_count} passed`} size="small" color="success" variant="outlined" />}
                  {testRun.failed_count > 0 && <Chip label={`${testRun.failed_count} failed`} size="small" color="error" variant="outlined" />}
                  {testRun.error_count > 0 && <Chip label={`${testRun.error_count} errors`} size="small" color="warning" variant="outlined" />}
                  {testRun.skipped_count > 0 && <Chip label={`${testRun.skipped_count} skipped`} size="small" variant="outlined" />}
                </Stack>
              )}

              {/* Completion banner */}
              {testRun && !isRunning && (
                <Alert
                  severity={testRun.error_count > 0 || testRun.skipped_count > 0 ? "warning" : testRun.failed_count > 0 ? "info" : "success"}
                  icon={
                    testRun.error_count === 0 && testRun.skipped_count === 0 && testRun.failed_count === 0 ? (
                      <CheckCircleOutlineIcon />
                    ) : (
                      <ErrorOutlineIcon />
                    )
                  }
                >
                  {testRun.passed_count === testRun.total_count
                    ? "All test cases passed!"
                    : testRun.error_count > 0 || testRun.skipped_count > 0
                      ? `Completed with ${testRun.error_count} error(s) and ${testRun.skipped_count} skipped. Check individual results for details.`
                      : `${testRun.passed_count} passed, ${testRun.failed_count} failed out of ${testRun.total_count} traces.`}
                </Alert>
              )}

              {/* Results table */}
              <MaterialReactTable table={table} />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>{isSetupPhase ? "Cancel" : "Close"}</Button>
          {isSetupPhase && (
            <Button variant="contained" onClick={handleRun} disabled={isEmpty || tooMany || createMutation.isPending}>
              {createMutation.isPending ? "Starting..." : "Run Test"}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* Annotation detail dialog */}
      <Dialog open={!!selectedAnnotationId} onClose={() => setSelectedAnnotationId("")} maxWidth="xl" fullWidth>
        <Details annotationId={selectedAnnotationId || undefined} onClose={() => setSelectedAnnotationId("")} onRerunComplete={() => {}} />
      </Dialog>
    </>
  );
};
