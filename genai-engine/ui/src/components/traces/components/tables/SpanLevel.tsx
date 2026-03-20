import {
  BucketProvider,
  CopyableChip as SharedCopyableChip,
  createSpanLevelColumns,
  DurationCellWithBucket,
  type ColumnDependencies as SharedColumnDependencies,
  TextOperators,
  TracesTable,
  TypeChip as SharedTypeChip,
} from "@arthur/shared-components";
import { Search } from "@mui/icons-material";
import { Alert, Box, Button, Paper, Stack, TextField } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import type { MRT_ColumnDef } from "material-react-table";
import { memo, useCallback, useMemo, useState } from "react";

import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { DataContentGate } from "../DataContentGate";
import { SpanStatusBadge } from "../span-status-badge";
import { isValidStatusCode } from "../StatusCode";
import { TraceContentCell } from "../TraceContentCell";

import { TracingFilterModal } from "./components/TracingFilterModal";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getFilteredSpans } from "@/services/tracing";
import { formatDate } from "@/utils/formatters";

const DEFAULT_DATA: SpanMetadataResponse[] = [];

interface SpanLevelProps {
  welcomeDismissed: boolean;
}

export const SpanLevel = memo(({ welcomeDismissed }: SpanLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const [, setDrawerTarget] = useDrawerTarget();
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });
  const [searchInput, setSearchInput] = useState("");

  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  // Sync filters with URL parameters
  useSyncFiltersToUrl();

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

  const sort: "asc" | "desc" = sorting[0]?.desc === false ? "asc" : "desc";

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters,
      timeRange,
      sort,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, filters, timeRange, sort]
  );

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.spans.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSpans(api, params),
  });

  const handleRowClick = useCallback(
    (row: SpanMetadataResponse) => {
      track(EVENT_NAMES.TRACING_DRAWER_OPENED, {
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

  const columns = useMemo(() => {
    const deps: SharedColumnDependencies = {
      formatDate,
      formatCurrency: () => "",
      onTrack: track,
      Chip: SharedCopyableChip,
      DurationCell: DurationCellWithBucket,
      TraceContentCell,
      AnnotationCell: () => null,
      SpanStatusBadge: SpanStatusBadge as SharedColumnDependencies["SpanStatusBadge"],
      TypeChip: SharedTypeChip,
      TokenCountTooltip,
      TokenCostTooltip,
      isValidStatusCode,
    };
    return createSpanLevelColumns(deps) as MRT_ColumnDef<SpanMetadataResponse, unknown>[];
  }, []);

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

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.spans?.map((span) => span.duration_ms) ?? []), [data?.spans]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  const hasData = Boolean(data?.spans?.length);

  return (
    <Stack gap={1} overflow="hidden">
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={hasActiveFilters} dataType="spans">
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
