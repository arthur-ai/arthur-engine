import { buildThresholdsFromSample } from "@arthur/shared-components";
import { BucketProvider, createSpanLevelColumns, TracesTable, useTraceColumnDependencies } from "@arthur/shared-components/traces";
import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import type { MRT_ColumnDef } from "material-react-table";
import { memo, useCallback, useMemo, useState } from "react";

import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { DataContentGate } from "../DataContentGate";

import { TraceFiltersBar } from "./components/TraceFiltersBar";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import type { SpanMetadataResponse, TraceSortBy } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { track, trackDynamic } from "@/services/analytics";
import { getFilteredSpans } from "@/services/tracing";

const DEFAULT_DATA: SpanMetadataResponse[] = [];

const SORTABLE_COLUMN_MAP: Record<string, TraceSortBy> = {
  start_time: "start_time",
  "token-count": "total_token_count",
  "token-cost": "total_token_cost",
};

interface SpanLevelProps {
  welcomeDismissed: boolean;
}

export const SpanLevel = memo(({ welcomeDismissed }: SpanLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const [, setDrawerTarget] = useDrawerTarget();
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  // Sync filters with URL parameters
  useSyncFiltersToUrl();

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

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
    queryKey: queryKeys.spans.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSpans(api, params),
  });

  const handleRowClick = useCallback(
    (row: SpanMetadataResponse) => {
      track("tracing/drawer_opened", {
        task_id: task?.id ?? "",
        level: "span",
        span_id: row.span_id,
        trace_id: row.trace_id,
        source: "table",
      });
      setContext({
        type: "span",
        ids: data?.spans?.map((span) => span.span_id) ?? [],
      });

      setDrawerTarget({ target: "span", id: row.span_id });
    },
    [data?.spans, setContext, setDrawerTarget, task?.id]
  );

  const columnDependencies = useTraceColumnDependencies({ onTrack: trackDynamic });

  const columns = useMemo(() => {
    const raw = createSpanLevelColumns(columnDependencies) as MRT_ColumnDef<SpanMetadataResponse, unknown>[];
    return raw.map((col) => {
      const colId = (col as { id?: string }).id ?? (col as { accessorKey?: string }).accessorKey ?? "";
      return { ...col, enableSorting: colId in SORTABLE_COLUMN_MAP };
    });
  }, [columnDependencies]);

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.spans?.map((span) => span.duration_ms) ?? []), [data?.spans]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  const hasData = Boolean(data?.spans?.length);

  return (
    <Stack
      sx={{
        gap: 1,
        overflow: "hidden",
      }}
    >
      <DataContentGate
        welcomeDismissed={welcomeDismissed}
        hasData={hasData}
        hasActiveFilters={hasActiveFilters}
        isLoading={isLoading}
        dataType="spans"
      >
        {/* Search bar and filter button */}
        {(hasData || hasActiveFilters || error) && <TraceFiltersBar />}

        {error && (
          <Box sx={{ p: 2 }}>
            <Alert severity="error">There was an error fetching spans.</Alert>
          </Box>
        )}

        {hasData && (
          <>
            <BucketProvider thresholds={thresholds}>
              <TracesTable
                data={data?.spans ?? DEFAULT_DATA}
                columns={columns}
                rowCount={data?.count ?? 0}
                pagination={pagination}
                onPaginationChange={props.onPaginationChange}
                isLoading={isLoading}
                onRowClick={handleRowClick}
                sorting={sorting}
                onSortingChange={setSorting}
              />
            </BucketProvider>
          </>
        )}
      </DataContentGate>
    </Stack>
  );
});
