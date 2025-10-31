import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { spanLevelColumns } from "../../data/span-level-columns";
import { useFilterStore } from "../../stores/filter.store";
import { useTracesHistoryStore } from "../../stores/history.store";
import { createFilterRow } from "../filtering/filters-row";
import { SPAN_FIELDS } from "../filtering/span-fields";

import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSpans } from "@/services/tracing";
import { TablePagination, Typography } from "@mui/material";
import { TracesEmptyState } from "../TracesEmptyState";
import { TracesTable } from "../TracesTable";

const DEFAULT_DATA: SpanMetadataResponse[] = [];

export const SpanLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const push = useTracesHistoryStore((state) => state.push);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const filters = useFilterStore((state) => state.filters);

  const { data, isFetching, isPlaceholderData } = useQuery({
    queryKey: queryKeys.spans.listPaginated(
      filters,
      pagination.page,
      pagination.rowsPerPage
    ),
    placeholderData: keepPreviousData,
    queryFn: () =>
      getFilteredSpans(api, {
        taskId: task?.id ?? "",
        page: pagination.page,
        pageSize: pagination.rowsPerPage,
        filters,
      }),
  });

  const [sorting, setSorting] = useState<SortingState>([
    { id: "start_time", desc: true },
  ]);

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

  return (
    <>
      <FiltersRow />
      {data?.spans?.length ? (
        <>
          <TracesTable
            table={table}
            loading={isFetching}
            onRowClick={(row) => {
              push({
                type: "span",
                id: row.original.span_id,
              });
            }}
          />

          <TablePagination
            component="div"
            count={data?.count ?? 0}
            onPageChange={pagination.handlePageChange}
            page={pagination.page}
            rowsPerPage={pagination.rowsPerPage}
            onRowsPerPageChange={pagination.handleRowsPerPageChange}
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
