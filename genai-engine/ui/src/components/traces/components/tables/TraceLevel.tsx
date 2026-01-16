import { Alert, Box, TablePagination } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { columns } from "../../data/columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useSyncFiltersToUrl } from "../../hooks/useSyncFiltersToUrl";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { DataContentGate } from "../DataContentGate";
import { createFilterRow } from "../filtering/filters-row";
import { TRACE_FIELDS } from "../filtering/trace-fields";
import { TracesTable } from "../TracesTable";

import { useApi } from "@/hooks/useApi";
import { usePagination } from "@/hooks/usePagination";
import { useTask } from "@/hooks/useTask";
import { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces } from "@/services/tracing";

const DEFAULT_DATA: TraceMetadataResponse[] = [];

interface TraceLevelProps {
  welcomeDismissed: boolean;
}

export function TraceLevel({ welcomeDismissed }: TraceLevelProps) {
  const { task } = useTask();
  const pagination = usePagination(FETCH_SIZE);

  const [, setDrawerTarget] = useDrawerTarget();

  const timeRange = useFilterStore((state) => state.timeRange);
  const filters = useFilterStore((state) => state.filters);

  // Sync filters with URL parameters
  useSyncFiltersToUrl();

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const api = useApi()!;

  const params = {
    taskId: task?.id ?? "",
    page: pagination.page,
    pageSize: pagination.rowsPerPage,
    filters,
    timeRange,
  };

  const { data, isFetching, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.traces.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredTraces(api, params),
  });

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

  const table = useReactTable({
    data: data?.traces ?? DEFAULT_DATA,
    columns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
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

  const handleRowClick = (row: TraceMetadataResponse) => {
    setContext({
      type: "trace",
      ids: data?.traces.map((trace) => trace.trace_id) ?? [],
    });

    setDrawerTarget({ target: "trace", id: row.trace_id });
  };

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.traces.map((trace) => trace.duration_ms) ?? []), [data?.traces]);

  // Check if any filters are active
  const hasActiveFilters = filters && Object.keys(filters).length > 0;

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching traces.</Alert>
      </Box>
    );
  }

  const hasData = Boolean(data?.traces?.length);

  return (
    <Box sx={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", overflow: "auto" }}>
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={hasActiveFilters} dataType="traces">
        {/* Only show FiltersRow if we have traces or if filters are active */}
        {(hasData || hasActiveFilters) && <FiltersRow />}

        {hasData && (
          <>
            <BucketProvider thresholds={thresholds}>
              <TracesTable
                table={table}
                loading={isFetching}
                onRowClick={(row) => {
                  handleRowClick(row.original);
                }}
              />
            </BucketProvider>
            <TablePagination
              component="div"
              count={data?.count ?? 0}
              onPageChange={pagination.handlePageChange}
              onRowsPerPageChange={pagination.handleRowsPerPageChange}
              page={pagination.page}
              rowsPerPage={pagination.rowsPerPage}
              rowsPerPageOptions={[10, 25, 50, 100]}
              sx={{
                overflow: "visible",
              }}
            />
          </>
        )}
      </DataContentGate>
    </Box>
  );
}
