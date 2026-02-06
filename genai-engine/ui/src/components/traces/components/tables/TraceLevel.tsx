import { Alert, Box, Stack } from "@mui/material";
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
import { FilterRow } from "../filtering/FilterRow";
import { IncomingFilter } from "../filtering/mapper";
import { TRACE_FIELDS } from "../filtering/trace-fields";
import { TraceContentCell } from "../TraceContentCell";

import { TracesTable } from "./TracesTable";

import { CopyableChip } from "@/components/common";
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
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [, setDrawerTarget] = useDrawerTarget();

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

  const columns = useMemo(
    () =>
      createTraceLevelColumns({
        formatDate,
        formatCurrency,
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
    []
  );

  const setFilters = useFilterStore((state) => state.setFilters);

  const handleFiltersChange = useCallback(
    (newFilters: IncomingFilter[]) => {
      setFilters(newFilters);
    },
    [setFilters]
  );

  const dynamicEnumArgMap = useMemo(
    () => ({
      trace_ids: { taskId: task?.id ?? "", api },
      session_ids: { taskId: task?.id ?? "", api },
      user_ids: { taskId: task?.id ?? "", api },
      span_ids: { taskId: task?.id ?? "", api },
    }),
    [task?.id, api]
  );

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.traces?.map((trace) => trace.duration_ms) ?? []), [data?.traces]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching traces.</Alert>
      </Box>
    );
  }

  const hasData = Boolean(data?.traces?.length);

  return (
    <Stack gap={1} height="100%" overflow="hidden">
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={hasActiveFilters} dataType="traces">
        {/* Only show FilterRow if we have traces or if filters are active */}
        {(hasData || hasActiveFilters) && (
          <FilterRow
            filters={filters}
            onFiltersChange={handleFiltersChange}
            fieldConfig={TRACE_FIELDS}
            dynamicEnumArgMap={dynamicEnumArgMap}
            onTrack={track}
          />
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
