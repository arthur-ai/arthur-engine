import { Search } from "@mui/icons-material";
import { Alert, Box, Button, Paper, Stack, TextField } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { memo, useCallback, useMemo, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { createTraceLevelColumns } from "../../data/create-trace-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { AnnotationCell } from "../AnnotationCell";
import { DataContentGate } from "../DataContentGate";
import { DurationCellWithBucket } from "../DurationCell";
import { TextOperators } from "../filtering/types";
import { TraceContentCell } from "../TraceContentCell";

import { TracingFilterModal } from "./components/TracingFilterModal";
import { TracesTable } from "./TracesTable";

import { CopyableChip } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getFilteredTraces } from "@/services/tracing";
import { formatCurrency, formatDate } from "@/utils/formatters";

const DEFAULT_DATA: TraceMetadataResponse[] = [];

interface TraceLevelProps {
  welcomeDismissed: boolean;
}

export const TraceLevel = memo(({ welcomeDismissed }: TraceLevelProps) => {
  const { task } = useTask();
  const { defaultCurrency } = useDisplaySettings();
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [, setDrawerTarget] = useDrawerTarget();
  const [searchInput, setSearchInput] = useState("");

  const timeRange = useFilterStore((state) => state.timeRange);
  const filters = useFilterStore((state) => state.filters);

  // Sync filters with URL parameters
  useSyncFiltersToUrl();

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const api = useApi()!;

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters,
      timeRange,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, filters, timeRange]
  );

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.traces.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredTraces(api, params),
  });

  const [sorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

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
    },
    [data?.traces, setContext, setDrawerTarget, task?.id]
  );

  const displayCurrency = data?.display_currency ?? defaultCurrency;

  const columns = useMemo(
    () =>
      createTraceLevelColumns({
        formatDate,
        formatCurrency: (amount: number) => formatCurrency(amount, displayCurrency),
        onTrack: track,
        Chip: CopyableChip,
        DurationCell: DurationCellWithBucket,
        TraceContentCell,
        AnnotationCell,
        SpanStatusBadge: () => null, // Not used in trace columns
        TypeChip: () => null, // Not used in trace columns
        TokenCountTooltip,
        TokenCostTooltip,
      }),
    [displayCurrency]
  );

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
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={hasActiveFilters} dataType="traces">
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

        {hasData && (
          <>
            <BucketProvider thresholds={thresholds}>
              <TracesTable
                data={data?.traces ?? DEFAULT_DATA}
                columns={columns}
                rowCount={data?.count ?? 0}
                pagination={pagination}
                onPaginationChange={props.onPaginationChange}
                isLoading={isLoading}
                onRowClick={handleRowClick}
                sorting={sorting}
              />
            </BucketProvider>
          </>
        )}
      </DataContentGate>
    </Stack>
  );
});
