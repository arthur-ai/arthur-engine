import { Alert, TablePagination, Typography } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { BucketProvider } from "../../context/bucket-context";
import { spanLevelColumns } from "../../data/span-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { usePaginationContext } from "../../stores/pagination-context";
import { buildThresholdsFromSample } from "../../utils/duration";
import { createFilterRow } from "../filtering/filters-row";
import { SPAN_FIELDS } from "../filtering/span-fields";
import { TracesEmptyState } from "../TracesEmptyState";
import { TracesTable } from "../TracesTable";

import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSpans } from "@/services/tracing";

const DEFAULT_DATA: SpanMetadataResponse[] = [];

export const SpanLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const [, setDrawerTarget] = useDrawerTarget();
  const pagination = useDatasetPagination(FETCH_SIZE);

  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const setContext = usePaginationContext((state) => state.actions.setContext);

  const params = {
    taskId: task?.id ?? "",
    page: pagination.page,
    pageSize: pagination.rowsPerPage,
    filters,
    timeRange,
  };

  const { data, isFetching, isPlaceholderData, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.spans.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSpans(api, params),
  });

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

  const table = useReactTable({
    data: data?.spans ?? DEFAULT_DATA,
    columns: spanLevelColumns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(SPAN_FIELDS, {
        trace_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  const handleRowClick = (row: SpanMetadataResponse) => {
    setContext({
      type: "span",
      ids: data?.spans.map((span) => span.span_id) ?? [],
    });

    setDrawerTarget({ target: "span", id: row.span_id });
  };

  const thresholds = useMemo(() => buildThresholdsFromSample(data?.spans.map((span) => span.duration_ms) ?? []), [data?.spans]);

  if (error) {
    return <Alert severity="error">There was an error fetching spans.</Alert>;
  }

  return (
    <>
      <FiltersRow />
      {data?.spans?.length ? (
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
            page={pagination.page}
            rowsPerPage={pagination.rowsPerPage}
            onRowsPerPageChange={pagination.handleRowsPerPageChange}
            rowsPerPageOptions={[10, 25, 50, 100]}
            disabled={isPlaceholderData}
            sx={{
              overflow: "visible",
            }}
          />
        </>
      ) : (
        <TracesEmptyState title="No spans found">
          <Typography variant="body1" color="text.secondary">
            Try adjusting your search query
          </Typography>
        </TracesEmptyState>
      )}
    </>
  );
};
