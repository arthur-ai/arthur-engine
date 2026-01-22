import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { memo, useCallback, useMemo, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { createSpanLevelColumns } from "../../data/create-span-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { DataContentGate } from "../DataContentGate";
import { DurationCellWithBucket } from "../DurationCell";
import { FilterRow } from "../filtering/FilterRow";
import { SPAN_FIELDS } from "../filtering/span-fields";
import { SpanStatusBadge } from "../span-status-badge";
import { isValidStatusCode } from "../StatusCode";
import { TraceContentCell } from "../TraceContentCell";

import { TracesTable } from "./TracesTable";

import { CopyableChip } from "@/components/common";
import { TypeChip } from "@/components/common/span/TypeChip";
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

  const columns = useMemo(
    () =>
      createSpanLevelColumns({
        formatDate,
        formatCurrency: () => "", // Not used in span columns but required by type
        onTrack: track,
        Chip: CopyableChip,
        DurationCell: DurationCellWithBucket,
        TraceContentCell,
        AnnotationCell: () => null, // Not used in span columns
        SpanStatusBadge,
        TypeChip,
        TokenCountTooltip,
        TokenCostTooltip,
        isValidStatusCode,
      }),
    [formatDate, track]
  );

  const setFilters = useFilterStore((state) => state.setFilters);

  const handleFiltersChange = useCallback(
    (newFilters: typeof filters) => {
      setFilters(newFilters);
    },
    [setFilters]
  );

  const dynamicEnumArgMap = useMemo(
    () => ({
      trace_ids: { taskId: task?.id ?? "", api },
      session_ids: { taskId: task?.id ?? "", api },
      span_ids: { taskId: task?.id ?? "", api },
      user_ids: { taskId: task?.id ?? "", api },
    }),
    [task?.id, api]
  );

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.spans?.map((span) => span.duration_ms) ?? []), [data?.spans]);

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
        {/* Only show FilterRow if we have spans or if filters are active */}
        {(hasData || hasActiveFilters) && (
          <FilterRow
            filters={filters}
            onFiltersChange={handleFiltersChange}
            fieldConfig={SPAN_FIELDS}
            dynamicEnumArgMap={dynamicEnumArgMap}
            onTrack={track}
          />
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
              />
            </BucketProvider>
          </>
        )}
      </DataContentGate>
    </Stack>
  );
});
