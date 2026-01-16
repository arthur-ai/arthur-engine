import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { MaterialReactTable } from "material-react-table";
import { memo, useCallback, useMemo, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { columns } from "../../data/columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useTable } from "../../hooks/useTable";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { DataContentGate } from "../DataContentGate";
import { createFilterRow } from "../filtering/filters-row";
import { TRACE_FIELDS } from "../filtering/trace-fields";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces } from "@/services/tracing";

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
      setContext({
        type: "trace",
        ids: data?.traces.map((trace) => trace.trace_id) ?? [],
      });

      setDrawerTarget({ target: "trace", id: row.trace_id });
    },
    [data?.traces, setContext, setDrawerTarget]
  );

  const table = useTable({
    data: data?.traces ?? DEFAULT_DATA,
    columns,
    pagination: { state: pagination, onChange: props.onPaginationChange },
    onRowClick: handleRowClick,
    state: {
      sorting,
      isLoading,
    },
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(TRACE_FIELDS, {
        trace_ids: { taskId: task?.id ?? "", api },
        session_ids: { taskId: task?.id ?? "", api },
        user_ids: { taskId: task?.id ?? "", api },
        span_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.traces.map((trace) => trace.duration_ms) ?? []), [data?.traces]);

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
        {/* Only show FiltersRow if we have traces or if filters are active */}
        {(hasData || hasActiveFilters) && <FiltersRow />}

        {hasData && (
          <>
            <BucketProvider thresholds={thresholds}>
              <MaterialReactTable table={table} />
            </BucketProvider>
          </>
        )}
      </DataContentGate>
    </Stack>
  );
});
