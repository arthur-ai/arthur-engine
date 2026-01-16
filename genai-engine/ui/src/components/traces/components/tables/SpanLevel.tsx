import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { MaterialReactTable } from "material-react-table";
import { memo, useCallback, useMemo, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { spanLevelColumns } from "../../data/span-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useTable } from "../../hooks/useTable";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { DataContentGate } from "../DataContentGate";
import { createFilterRow } from "../filtering/filters-row";
import { SPAN_FIELDS } from "../filtering/span-fields";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSpans } from "@/services/tracing";

const DEFAULT_DATA: SpanMetadataResponse[] = [];

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
    queryKey: queryKeys.spans.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSpans(api, params),
  });

  const [sorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

  const handleRowClick = useCallback(
    (row: SpanMetadataResponse) => {
      setContext({
        type: "span",
        ids: data?.spans.map((span) => span.span_id) ?? [],
      });

      setDrawerTarget({ target: "span", id: row.span_id });
    },
    [data?.spans, setContext, setDrawerTarget]
  );

  const table = useTable({
    data: data?.spans ?? DEFAULT_DATA,
    columns: spanLevelColumns,
    pagination: {
      state: pagination,
      onChange: props.onPaginationChange,
      rowCount: data?.count ?? 0,
    },
    onRowClick: handleRowClick,
    state: {
      sorting,
      isLoading,
    },
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(SPAN_FIELDS, {
        trace_ids: { taskId: task?.id ?? "", api },
        session_ids: { taskId: task?.id ?? "", api },
        span_ids: { taskId: task?.id ?? "", api },
        user_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.spans.map((span) => span.duration_ms) ?? []), [data?.spans]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching spans.</Alert>
      </Box>
    );
  }

  const hasData = Boolean(data?.spans?.length);

  return (
    <Stack gap={1} overflow="hidden">
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={hasActiveFilters} dataType="spans">
        {/* Only show FiltersRow if we have spans or if filters are active */}
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
