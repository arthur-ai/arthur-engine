import { TracesEmptyState } from "@arthur/shared-components";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import ReplayIcon from "@mui/icons-material/Replay";
import { Box, Button, Chip, CircularProgress, Dialog, DialogContent, DialogTitle, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { PaginationState } from "@tanstack/react-table";
import { createMRTColumnHelper, MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { useCallback, useMemo, useState } from "react";

import { testRunResultsQueryOptions, useCreateTestRun, useDeleteTestRun, useTestRun, useTestRunResults, useTestRunsList } from "../hooks/useTestRun";

import { CopyableChip } from "@/components/common";
import { Details } from "@/components/live-evals/components/results/components/details";
import { serializeDrawerTarget } from "@/components/traces/hooks/useDrawerTarget";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import type { AgenticAnnotationResponse, ContinuousEvalTestRunResponse } from "@/lib/api-client/api-client";
import { formatCurrency, formatDateInTimezone } from "@/utils/formatters";
import { getStatusChipSx } from "@/utils/statusChipStyles";

// --- Test run list columns ---

const testRunColumnHelper = createMRTColumnHelper<ContinuousEvalTestRunResponse>();

function createTestRunColumns({ timezone, use24Hour, onDelete }: { timezone: string; use24Hour: boolean; onDelete: (testRunId: string) => void }) {
  return [
    testRunColumnHelper.accessor("created_at", {
      header: "Date",
      Cell: ({ cell }) => <Typography variant="body2">{formatDateInTimezone(cell.getValue(), timezone, { hour12: !use24Hour })}</Typography>,
    }),
    testRunColumnHelper.accessor("status", {
      header: "Status",
      Cell: ({ cell }) => {
        const status = cell.getValue();
        const label = status === "partial_failure" ? "Partial Failure" : status;
        return <Chip label={label} size="small" variant="outlined" sx={getStatusChipSx(status === "partial_failure" ? "warning" : status)} />;
      },
    }),
    testRunColumnHelper.accessor("passed_count", {
      header: "Passed",
      Cell: ({ cell, row }) => (
        <Typography variant="body2" color={cell.getValue() > 0 ? "success.main" : "text.secondary"}>
          {cell.getValue()}/{row.original.total_count}
        </Typography>
      ),
    }),
    testRunColumnHelper.accessor("failed_count", {
      header: "Failed",
      Cell: ({ cell }) => (
        <Typography variant="body2" color={cell.getValue() > 0 ? "error.main" : "text.secondary"}>
          {cell.getValue()}
        </Typography>
      ),
    }),
    testRunColumnHelper.accessor("error_count", {
      header: "Errors",
      Cell: ({ cell }) => (
        <Typography variant="body2" color={cell.getValue() > 0 ? "error.main" : "text.secondary"}>
          {cell.getValue()}
        </Typography>
      ),
    }),
    testRunColumnHelper.accessor("total_count", {
      header: "Traces",
      Cell: ({ cell }) => <Typography variant="body2">{cell.getValue()}</Typography>,
    }),
    testRunColumnHelper.display({
      id: "actions",
      header: "",
      size: 48,
      Cell: ({ row }) => (
        <Tooltip title="Delete test run">
          <IconButton
            size="small"
            color="error"
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation();
              onDelete(row.original.id);
            }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      ),
    }),
  ];
}

// --- Test run results modal ---

function TestRunResultsModal({
  testRun,
  taskId,
  evalId,
  onClose,
  onSwitchTestRun,
}: {
  testRun: ContinuousEvalTestRunResponse;
  taskId: string;
  evalId: string;
  onClose: () => void;
  onSwitchTestRun: (testRun: ContinuousEvalTestRunResponse) => void;
}) {
  const api = useApi()!;
  const { defaultCurrency } = useDisplaySettings();
  const queryClient = useQueryClient();
  const createTestRun = useCreateTestRun(evalId);
  const [selectedAnnotationId, setSelectedAnnotationId] = useState("");

  const { data: liveTestRun } = useTestRun(testRun.id);
  const displayTestRun = liveTestRun ?? testRun;

  const resultsQueryOpts = testRunResultsQueryOptions({ api, testRunId: testRun.id, pageSize: 50 });
  const { data: resultsData, isLoading } = useTestRunResults(testRun.id);

  const handleRunAgain = async () => {
    const results = await queryClient.fetchQuery(resultsQueryOpts);
    const traceIds = results.annotations.map((a) => a.trace_id);
    if (traceIds.length > 0) {
      const newTestRun = await createTestRun.mutateAsync(traceIds);
      onSwitchTestRun(newTestRun);
    }
  };

  const columns = useMemo(
    () => [
      resultColumnHelper.accessor("trace_id", {
        header: "Trace ID",
        Cell: ({ cell }) => <CopyableChip label={cell.getValue()} sx={{ fontFamily: "monospace", fontSize: "0.75rem" }} />,
      }),
      resultColumnHelper.accessor("run_status", {
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
      resultColumnHelper.accessor("annotation_score", {
        header: "Score",
        Cell: ({ cell }) => {
          const score = cell.getValue();
          return <Typography variant="body2">{score != null ? score : "—"}</Typography>;
        },
      }),
      resultColumnHelper.accessor("annotation_description", {
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
      resultColumnHelper.accessor("cost", {
        header: "Cost",
        Cell: ({ cell }) => {
          const cost = cell.getValue();
          return <Typography variant="body2">{cost != null ? formatCurrency(cost, defaultCurrency) : "—"}</Typography>;
        },
      }),
      resultColumnHelper.display({
        id: "view_trace",
        header: "",
        size: 48,
        Cell: ({ row }) => (
          <Tooltip title="View trace">
            <IconButton
              size="small"
              component="a"
              href={`/tasks/${taskId}/traces${serializeDrawerTarget({ target: "trace", id: row.original.trace_id })}`}
              target="_blank"
              rel="noopener noreferrer"
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

  const table = useMaterialReactTable({
    columns,
    data: resultsData?.annotations ?? [],
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

  return (
    <>
      <Dialog open onClose={onClose} maxWidth="xl" fullWidth>
        <DialogTitle>
          <Stack direction="row" alignItems="center" gap={2}>
            <Typography variant="h6">Test Run Results</Typography>
            <Stack direction="row" gap={1}>
              {displayTestRun.passed_count > 0 && (
                <Chip label={`${displayTestRun.passed_count} passed`} size="small" color="success" variant="outlined" />
              )}
              {displayTestRun.failed_count > 0 && (
                <Chip label={`${displayTestRun.failed_count} failed`} size="small" color="error" variant="outlined" />
              )}
              {displayTestRun.error_count > 0 && (
                <Chip label={`${displayTestRun.error_count} errors`} size="small" color="warning" variant="outlined" />
              )}
              {displayTestRun.skipped_count > 0 && <Chip label={`${displayTestRun.skipped_count} skipped`} size="small" variant="outlined" />}
            </Stack>
            <Box sx={{ flex: 1 }} />
            <Button size="small" startIcon={<ReplayIcon />} onClick={handleRunAgain} disabled={createTestRun.isPending}>
              {createTestRun.isPending ? "Starting..." : "Run Again"}
            </Button>
            <IconButton size="small" onClick={onClose}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Stack>
        </DialogTitle>
        <DialogContent sx={{ p: 0 }}>
          {isLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <MaterialReactTable table={table} />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!selectedAnnotationId} onClose={() => setSelectedAnnotationId("")} maxWidth="xl" fullWidth>
        <Details annotationId={selectedAnnotationId || undefined} onClose={() => setSelectedAnnotationId("")} onRerunComplete={() => {}} />
      </Dialog>
    </>
  );
}

// --- Result columns (shared) ---

const resultColumnHelper = createMRTColumnHelper<AgenticAnnotationResponse>();

// --- Main component ---

const DEFAULT_DATA: ContinuousEvalTestRunResponse[] = [];

export const TestRunsHistory = ({ evalId, taskId }: { evalId: string; taskId: string }) => {
  const { timezone, use24Hour } = useDisplaySettings();
  const [pagination, setPagination] = useState<PaginationState>({ pageIndex: 0, pageSize: 10 });
  const [selectedTestRun, setSelectedTestRun] = useState<ContinuousEvalTestRunResponse | null>(null);

  const { data, isLoading, isFetching } = useTestRunsList(evalId, pagination.pageIndex, pagination.pageSize);
  const deleteTestRun = useDeleteTestRun(evalId);
  const handleDelete = useCallback((id: string) => deleteTestRun.mutate(id), [deleteTestRun]);

  const testRunColumns = useMemo(() => createTestRunColumns({ timezone, use24Hour, onDelete: handleDelete }), [timezone, use24Hour, handleDelete]);

  const table = useMaterialReactTable({
    columns: testRunColumns,
    data: data?.test_runs ?? DEFAULT_DATA,
    manualPagination: true,
    onPaginationChange: setPagination,
    state: { pagination, isLoading, showProgressBars: isFetching },
    rowCount: data?.count ?? 0,
    enableTopToolbar: false,
    enableColumnActions: false,
    enableColumnFilters: false,
    enableGlobalFilter: false,
    enableSorting: false,
    muiTablePaperProps: { elevation: 0, sx: { border: "none" } },
    renderEmptyRowsFallback: () => (
      <Box sx={{ p: 2 }}>
        <TracesEmptyState title='No test runs yet. Click "Test Eval" to run your first test.' />
      </Box>
    ),
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => setSelectedTestRun(row.original),
      sx: { cursor: "pointer" },
    }),
  });

  return (
    <>
      <MaterialReactTable table={table} />

      {selectedTestRun && (
        <TestRunResultsModal
          testRun={selectedTestRun}
          taskId={taskId}
          evalId={evalId}
          onClose={() => setSelectedTestRun(null)}
          onSwitchTestRun={setSelectedTestRun}
        />
      )}
    </>
  );
};
