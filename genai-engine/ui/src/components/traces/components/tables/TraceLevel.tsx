import {
  BucketProvider,
  CopyableChip as SharedCopyableChip,
  createTraceLevelColumns,
  DurationCellWithBucket,
  type ColumnDependencies as SharedColumnDependencies,
  TextOperators,
  TracesTable,
} from "@arthur/shared-components";
import { Search } from "@mui/icons-material";
import { Alert, Box, Button, Paper, Stack, TextField } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type OnChangeFn, type PaginationState, type RowSelectionState, SortingState } from "@tanstack/react-table";
import type { MRT_ColumnDef } from "material-react-table";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { AnnotationCell } from "../AnnotationCell";
import { DataContentGate } from "../DataContentGate";
import { TraceContentCell } from "../TraceContentCell";

import { EvalPickerDialog } from "./components/EvalPickerDialog";
import { SelectionActionBar } from "./components/SelectionActionBar";
import { TracingFilterModal } from "./components/TracingFilterModal";

import { TestRunDialog } from "@/components/live-evals/components/TestRunDialog";
import { DATA_TOUR } from "@/components/onboarding/data-tour";
import { useCompleteStep } from "@/components/onboarding/hooks/useCompleteStep";
import { useStepAction } from "@/components/onboarding/hooks/useStepAction";
import { STEP_IDS } from "@/components/onboarding/steps";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import type { TraceSortBy, TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE, MAX_TRACES_PER_TEST_RUN } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getFilteredTraces } from "@/services/tracing";
import { formatCurrency, formatDateInTimezone } from "@/utils/formatters";

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

export const TraceLevel = memo(({ welcomeDismissed }: TraceLevelProps) => {
  const { task } = useTask();
  const { defaultCurrency, timezone, use24Hour } = useDisplaySettings();
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [drawerTarget, setDrawerTarget] = useDrawerTarget();
  const [searchInput, setSearchInput] = useState("");
  const completeInspectTraceStep = useCompleteStep(STEP_IDS.INSPECT_TRACE);
  const completeReviewTraceStep = useCompleteStep(STEP_IDS.REVIEW_TRACE);

  const previousDrawerIdRef = useRef(drawerTarget?.id);
  useEffect(() => {
    if (previousDrawerIdRef.current && !drawerTarget?.id) {
      completeReviewTraceStep();
    }
    previousDrawerIdRef.current = drawerTarget?.id;
  }, [drawerTarget?.id, completeReviewTraceStep]);

  useStepAction(STEP_IDS.REVIEW_TRACE, () => {
    setDrawerTarget({ id: null });
  });

  const timeRange = useFilterStore((state) => state.timeRange);
  const filters = useFilterStore((state) => state.filters);

  // Sync filters with URL parameters
  useSyncFiltersToUrl();

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const api = useApi()!;

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [evalPickerOpen, setEvalPickerOpen] = useState(false);
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

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
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

  const handleTestRunClose = useCallback(() => {
    setTestRunConfig(null);
    setRowSelection({});
  }, []);

  const handleClearSelection = useCallback(() => {
    setRowSelection({});
  }, []);

  const handleRowClick = useCallback(
    (row: TraceMetadataResponse) => {
      track(EVENT_NAMES.TRACING_DRAWER_OPENED, {
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
      completeInspectTraceStep();
    },
    [data?.traces, setContext, setDrawerTarget, task?.id, completeInspectTraceStep]
  );

  useStepAction(STEP_IDS.INSPECT_TRACE, () => {
    const firstTrace = data?.traces?.[0];
    if (firstTrace) handleRowClick(firstTrace);
  });

  const displayCurrency = data?.display_currency ?? defaultCurrency;

  const columns = useMemo(() => {
    const deps: SharedColumnDependencies = {
      formatDate: (v) => formatDateInTimezone(v, timezone, { hour12: !use24Hour }),
      formatCurrency: (amount: number) => formatCurrency(amount, displayCurrency),
      onTrack: track,
      Chip: SharedCopyableChip,
      DurationCell: DurationCellWithBucket,
      TraceContentCell,
      AnnotationCell: AnnotationCell as unknown as SharedColumnDependencies["AnnotationCell"],
      SpanStatusBadge: () => null,
      TypeChip: () => null,
      TokenCountTooltip,
      TokenCostTooltip,
    };
    const raw = createTraceLevelColumns(deps) as MRT_ColumnDef<TraceMetadataResponse, unknown>[];
    return raw.map((col) => {
      const colId = (col as { id?: string }).id ?? (col as { accessorKey?: string }).accessorKey ?? "";
      return { ...col, enableSorting: colId in SORTABLE_COLUMN_MAP };
    });
  }, [displayCurrency, timezone, use24Hour]);

  const setFilters = useFilterStore((state) => state.setFilters);

  const handleSearch = useCallback(() => {
    if (searchInput.trim()) {
      const existingFilters = filters.filter((f) => f.name !== "span_name");
      setFilters([
        ...existingFilters,
        {
          name: "span_name",
          operator: TextOperators.CONTAINS,
          value: searchInput.trim(),
        },
      ]);
    } else {
      // Clear the span_name filter if search is empty
      setFilters(filters.filter((f) => f.name !== "span_name"));
    }
  }, [searchInput, filters, setFilters]);

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.traces?.map((trace) => trace.duration_ms) ?? []), [data?.traces]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  const hasData = Boolean(data?.traces?.length);

  return (
    <Stack gap={1} height="100%" overflow="hidden">
      <DataContentGate
        welcomeDismissed={welcomeDismissed}
        hasData={hasData}
        hasActiveFilters={hasActiveFilters}
        isLoading={isLoading}
        dataType="traces"
      >
        {/* Search bar and filter button */}
        {(hasData || hasActiveFilters || error) && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <TextField
                size="small"
                placeholder="Search by span name"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSearch();
                  }
                }}
                sx={{ width: 300 }}
              />
              <Button variant="outlined" startIcon={<Search />} onClick={handleSearch}>
                Search
              </Button>
              <TracingFilterModal />
            </Stack>
          </Paper>
        )}

        {error && (
          <Box sx={{ p: 2 }}>
            <Alert severity="error">There was an error fetching traces.</Alert>
          </Box>
        )}

        <SelectionActionBar selectedCount={selectedTraceIds.length} onRunEval={handleRunEvalClick} onClearSelection={handleClearSelection} />

        {hasData && (
          <BucketProvider thresholds={thresholds}>
            <Box data-tour={DATA_TOUR.TRACES_TABLE} sx={{ minHeight: 0, display: "flex", flexDirection: "column" }}>
              <TracesTable
                data={data?.traces ?? DEFAULT_DATA}
                columns={columns as MRT_ColumnDef<TraceMetadataResponse, unknown>[]}
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
              />
            </Box>
          </BucketProvider>
        )}
      </DataContentGate>

      <EvalPickerDialog open={evalPickerOpen} onClose={() => setEvalPickerOpen(false)} onSelect={handleEvalSelected} />

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
