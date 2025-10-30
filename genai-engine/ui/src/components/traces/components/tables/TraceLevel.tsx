import {
  LinearProgress,
  TableRow,
  TableHead,
  Paper,
  Table,
  TableContainer,
  Box,
  TableBody,
  TableSortLabel,
  TableCell,
  Alert,
} from "@mui/material";
import { useInfiniteQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useSelector } from "@xstate/store/react";
import { useMemo, useState } from "react";

import { columns } from "../../data/columns";
import { useTableScrollThrottler } from "../../hooks/useTableScrollThrottler";
import { useTracesStore } from "../../store";
import { createFilterRow } from "../filtering/filters-row";
import { useFilterStore } from "../filtering/stores/filter.store";
import { TRACE_FIELDS } from "../filtering/trace-fields";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { TraceResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { getTracesInfiniteQueryOptions } from "@/query-options/traces";

const DEFAULT_DATA: TraceResponse[] = [];

export function TraceLevel() {
  const { task } = useTask();

  const [, store] = useTracesStore(() => null);

  const filterStore = useFilterStore();
  const filters = useSelector(filterStore, (state) => state.context.filters);

  const api = useApi()!;

  const { data, fetchNextPage, isFetching, error } = useInfiniteQuery({
    ...getTracesInfiniteQueryOptions({ api, taskId: task?.id ?? "", filters }),
  });

  const flatData = useMemo(
    () => data?.pages?.flatMap((page) => page.traces) ?? [],
    [data]
  );

  const totalDBRowCount = data?.pages?.[0]?.count ?? 0;

  const [sorting, setSorting] = useState<SortingState>([
    { id: "start_time", desc: true },
  ]);

  const table = useReactTable({
    data: flatData ?? DEFAULT_DATA, // Use test data to verify scrolling
    columns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    debugTable: true,
    debugHeaders: true,
    debugColumns: true,
  });

  const { execute, ref } = useTableScrollThrottler({
    onOffsetReached: fetchNextPage,
    enabled: !isFetching && totalDBRowCount >= FETCH_SIZE,
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(TRACE_FIELDS, {
        trace_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  if (error) {
    return <Alert severity="error">There was an error fetching traces.</Alert>;
  }

  return (
    <>
      <FiltersRow />
      <TableContainer
        component={Paper}
        sx={{ flexGrow: 1 }}
        ref={ref}
        onScroll={(e) => {
          execute(e.currentTarget);
        }}
      >
        {isFetching && <LinearProgress />}
        <Table stickyHeader size="small">
          <TableHead>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableCell
                    key={header.id}
                    colSpan={header.colSpan}
                    sx={{
                      backgroundColor: "grey.50",
                    }}
                    sortDirection={header.column.getIsSorted()}
                  >
                    <TableSortLabel
                      disabled={!header.column.getCanSort()}
                      active={header.column.getIsSorted() !== false}
                      direction={header.column.getIsSorted() || undefined}
                      onClick={() => {
                        table.setSorting((prev) => [
                          { id: header.column.id, desc: !prev[0].desc },
                        ]);
                      }}
                    >
                      <Box sx={{ width: header.getSize() }}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </Box>
                    </TableSortLabel>
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableHead>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                hover
                onClick={() => {
                  store.send({
                    type: "openDrawer",
                    for: "trace",
                    id: row.original.trace_id,
                  });
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell
                    key={cell.id}
                    sx={{
                      maxWidth: cell.column.getSize(),
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </>
  );
}
