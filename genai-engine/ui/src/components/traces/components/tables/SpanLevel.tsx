import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useSelector } from "@xstate/store/react";
import { useMemo, useState } from "react";

import { spanLevelColumns } from "../../data/span-level-columns";
import { useTableScrollThrottler } from "../../hooks/useTableScrollThrottler";
import { useTracesStore } from "../../store";
import { createFilterRow } from "../filtering/filters-row";
import { SPAN_FIELDS } from "../filtering/span-fields";
import { useFilterStore } from "../filtering/stores/filter.store";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { FETCH_SIZE } from "@/lib/constants";
import { getSpansInfiniteQueryOptions } from "@/query-options/spans";
import { TracesTable } from "../TracesTable";
import { TracesEmptyState } from "../TracesEmptyState";
import { TablePagination, Typography } from "@mui/material";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSpans } from "@/services/tracing";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";

const DEFAULT_DATA: SpanMetadataResponse[] = [];

export const SpanLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const [, store] = useTracesStore(() => null);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const filters = useSelector(
    useFilterStore(),
    (state) => state.context.filters
  );

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
              store.send({
                type: "openDrawer",
                for: "span",
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
