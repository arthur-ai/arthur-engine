import { buildThresholdsFromSample } from "@arthur/shared-components";
import {
  BucketProvider,
  createTraceLevelColumns,
  TraceDisplaySettingsProvider,
  TracesTable,
  useTraceColumnDependencies,
  useTraceDisplaySettings,
} from "@arthur/shared-components/traces";
import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type OnChangeFn, type PaginationState, type RowSelectionState, SortingState } from "@tanstack/react-table";
import { isAxiosError } from "axios";
import type { MRT_ColumnDef } from "material-react-table";
import { useSnackbar } from "notistack";
import { type ComponentProps, memo, useCallback, useMemo, useState } from "react";

import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useAnnotationCellOptions } from "../../hooks/useTraceAnnotationActions";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { BulkAddToDatasetDialog } from "../add-to-dataset/BulkAddToDatasetDialog";
import { useBulkAddTracesToDataset } from "../add-to-dataset/hooks/useBulkAddTracesToDataset";
import { DataContentGate } from "../DataContentGate";

import { EvalPickerDialog } from "./components/EvalPickerDialog";
import { SelectionActionBar } from "./components/SelectionActionBar";
import { TraceFiltersBar } from "./components/TraceFiltersBar";

import { TestRunDialog } from "@/components/live-evals/components/TestRunDialog";
import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import type { TraceSortBy, TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE, MAX_TRACES_PER_TEST_RUN } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { track, trackDynamic } from "@/services/analytics";
import { getFilteredTraces } from "@/services/tracing";

const DEFAULT_DATA: TraceMetadataResponse[] = [];

const SORTABLE_COLUMN_MAP: Record<string, TraceSortBy> = {
  start_time: "start_time",
  "token-count": "total_token_count",
  "token-cost": "total_token_cost",
  span_count: "span_count",
};

interface TraceLevelProps {
  welcomeDismissed: boolean;
}

type TraceLevelTableProps = Omit<ComponentProps<typeof TracesTable<TraceMetadataResponse>>, "columns" | "rowCount" | "hasNextPage"> & {
  rowCount: number;
};

const TraceLevelTable = (props: TraceLevelTableProps) => {
  const annotationCell = useAnnotationCellOptions();
  const columnDependencies = useTraceColumnDependencies({ onTrack: trackDynamic, annotationCell });

  const columns = useMemo(() => {
    const raw = createTraceLevelColumns(columnDependencies) as MRT_ColumnDef<TraceMetadataResponse, unknown>[];
    return raw.map((col) => {
      const colId = (col as { id?: string }).id ?? (col as { accessorKey?: string }).accessorKey ?? "";
      return { ...col, enableSorting: colId in SORTABLE_COLUMN_MAP };
    });
  }, [columnDependencies]);

  return <TracesTable columns={columns} {...props} />;
};

export const TraceLevel = memo(({ welcomeDismissed }: TraceLevelProps) => {
  const { task } = useTask();
  const displaySettings = useTraceDisplaySettings();
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [, setDrawerTarget] = useDrawerTarget();

  const timeRange = useFilterStore((state) => state.timeRange);
  const filters = useFilterStore((state) => state.filters);

  // Sync filters with URL parameters
  useSyncFiltersToUrl();

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const api = useApi()!;
  const { enqueueSnackbar } = useSnackbar();

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [evalPickerOpen, setEvalPickerOpen] = useState(false);
  const [addToDatasetPickerOpen, setAddToDatasetPickerOpen] = useState(false);
  const [testRunConfig, setTestRunConfig] = useState<{ evalId: string; evalName: string; testRunId: string } | null>(null);

  // Clear selection when sorting or pagination changes (owned setters)
  const handleSortingChange = useCallback<OnChangeFn<SortingState>>((updater) => {
    setSorting(updater);
    setRowSelection({});
  }, []);

  const handlePaginationChange = useCallback<OnChangeFn<PaginationState>>(
    (updater) => {
      props.onPaginationChange(updater);
      setRowSelection({});
    },
    [props]
  );

  // Clear selection when filters or timeRange change (zustand store — not our setters)
  const [prevFilters, setPrevFilters] = useState(filters);
  const [prevTimeRange, setPrevTimeRange] = useState(timeRange);
  if (prevFilters !== filters || prevTimeRange !== timeRange) {
    setPrevFilters(filters);
    setPrevTimeRange(timeRange);
    setRowSelection({});
  }

  const sort: "asc" | "desc" = sorting[0]?.desc === false ? "asc" : "desc";
  const sortBy = SORTABLE_COLUMN_MAP[sorting[0]?.id] ?? "start_time";

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters,
      timeRange,
      sort,
      sortBy,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, filters, timeRange, sort, sortBy]
  );

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.traces.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredTraces(api, params),
  });

  const selectedTraceIds = useMemo(() => Object.keys(rowSelection).filter((k) => rowSelection[k]), [rowSelection]);

  const handleRunEvalClick = useCallback(() => {
    setEvalPickerOpen(true);
  }, []);

  // Hoist the mutation: fire it in the click handler, pass testRunId down
  const handleEvalSelected = useCallback(
    async (eval_: { id: string; name: string }) => {
      setEvalPickerOpen(false);
      const unique = [...new Set(selectedTraceIds)].slice(0, MAX_TRACES_PER_TEST_RUN);
      if (unique.length === 0) return;
      try {
        const createTestRun = api.api.createTestRunApiV1ContinuousEvalsEvalIdTestRunsPost(eval_.id, {
          trace_ids: unique,
        });
        const result = await createTestRun;
        setTestRunConfig({ evalId: eval_.id, evalName: eval_.name, testRunId: result.data.id });
      } catch {
        // error is surfaced by the API interceptor / snackbar
      }
    },
    [selectedTraceIds, api]
  );

  const bulkAddToDataset = useBulkAddTracesToDataset({
    onSuccess: (result) => {
      const { success_count, total } = result;
      const variant = success_count === total ? "success" : success_count === 0 ? "error" : "warning";
      enqueueSnackbar(`${success_count} of ${total} added`, { variant });
      if (success_count > 0) {
        setRowSelection({});
      }
    },
    onError: (error) => {
      const detail = isAxiosError(error) ? error.response?.data?.detail : undefined;
      enqueueSnackbar(detail || "Failed to add traces to dataset", { variant: "error" });
    },
  });

  const handleAddToDatasetClick = useCallback(() => {
    setAddToDatasetPickerOpen(true);
  }, []);

  const handleAddToDatasetSelected = useCallback(
    async ({ datasetId, transformId }: { datasetId: string; transformId: string }) => {
      const unique = [...new Set(selectedTraceIds)];
      if (unique.length === 0) return;
      try {
        await bulkAddToDataset.mutateAsync({ datasetId, transformId, traceIds: unique });
      } catch {
        // error surfaced via onError toast above
      } finally {
        setAddToDatasetPickerOpen(false);
      }
    },
    [selectedTraceIds, bulkAddToDataset]
  );

  const handleTestRunClose = useCallback(() => {
    setTestRunConfig(null);
    setRowSelection({});
  }, []);

  const handleClearSelection = useCallback(() => {
    setRowSelection({});
  }, []);

  const handleRowClick = useCallback(
    (row: TraceMetadataResponse) => {
      track("tracing/drawer_opened", {
        task_id: task?.id ?? "",
        level: "trace",
        trace_id: row.trace_id,
        source: "table",
      });
      setContext({
        type: "trace",
        ids: data?.traces?.map((trace) => trace.trace_id) ?? [],
      });

      setDrawerTarget({ target: "trace", id: row.trace_id });
      dispatchTourEvent(TASK_TOUR_EVENTS.traceOpened);
      dispatchTourEvent(TASK_TOUR_EVENTS.deployVerified);
    },
    [data?.traces, setContext, setDrawerTarget, task?.id]
  );

  // Costs come in the currency the server reports for this page.
  const tableDisplaySettings = useMemo(
    () => ({ ...displaySettings, currency: data?.display_currency ?? displaySettings.currency }),
    [displaySettings, data?.display_currency]
  );

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.traces?.map((trace) => trace.duration_ms) ?? []), [data?.traces]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  const hasData = Boolean(data?.traces?.length);

  return (
    <Stack
      sx={{
        gap: 1,
        height: "100%",
        overflow: "hidden",
      }}
    >
      <DataContentGate
        welcomeDismissed={welcomeDismissed}
        hasData={hasData}
        hasActiveFilters={hasActiveFilters}
        isLoading={isLoading}
        dataType="traces"
      >
        {/* Search bar and filter button */}
        {(hasData || hasActiveFilters || error) && <TraceFiltersBar />}

        {error && (
          <Box sx={{ p: 2 }}>
            <Alert severity="error">There was an error fetching traces.</Alert>
          </Box>
        )}

        <SelectionActionBar
          selectedCount={selectedTraceIds.length}
          onRunEval={handleRunEvalClick}
          onAddToDataset={handleAddToDatasetClick}
          onClearSelection={handleClearSelection}
        />

        {hasData && (
          <BucketProvider thresholds={thresholds}>
            <Box sx={{ height: "100%", minHeight: 0, display: "flex", flexDirection: "column" }}>
              <TraceDisplaySettingsProvider value={tableDisplaySettings}>
                <TraceLevelTable
                  data={data?.traces ?? DEFAULT_DATA}
                  rowCount={data?.count ?? 0}
                  pagination={pagination}
                  onPaginationChange={handlePaginationChange}
                  isLoading={isLoading}
                  onRowClick={handleRowClick}
                  sorting={sorting}
                  onSortingChange={handleSortingChange}
                  enableRowSelection
                  rowSelection={rowSelection}
                  onRowSelectionChange={setRowSelection}
                  getRowId={(row) => row.trace_id}
                  getRowProps={({ rowIndex }) => (rowIndex === 0 ? { "data-tour-id": TOUR_IDS.tracesFirstRow } : {})}
                />
              </TraceDisplaySettingsProvider>
            </Box>
          </BucketProvider>
        )}
      </DataContentGate>

      <EvalPickerDialog open={evalPickerOpen} onClose={() => setEvalPickerOpen(false)} onSelect={handleEvalSelected} />

      <BulkAddToDatasetDialog
        open={addToDatasetPickerOpen}
        traceCount={selectedTraceIds.length}
        isSubmitting={bulkAddToDataset.isPending}
        onClose={() => setAddToDatasetPickerOpen(false)}
        onSelect={handleAddToDatasetSelected}
      />

      <TestRunDialog
        open={!!testRunConfig}
        onClose={handleTestRunClose}
        evalId={testRunConfig?.evalId ?? ""}
        evalName={testRunConfig?.evalName ?? ""}
        taskId={task?.id ?? ""}
        testRunId={testRunConfig?.testRunId}
      />
    </Stack>
  );
});
