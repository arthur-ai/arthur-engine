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
import { Alert } from "@mui/material";

export const SpanLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const [, store] = useTracesStore(() => null);

  const filters = useSelector(
    useFilterStore(),
    (state) => state.context.filters
  );

  const { data, isFetching, fetchNextPage, error } = useInfiniteQuery({
    ...getSpansInfiniteQueryOptions({ api, taskId: task?.id ?? "", filters }),
  });

  const [sorting, setSorting] = useState<SortingState>([
    { id: "start_time", desc: true },
  ]);

  const flatData = useMemo(
    () => data?.pages?.flatMap((page) => page.spans) ?? [],
    [data]
  );

  const totalDBRowCount = data?.pages?.[0]?.count ?? 0;

  const table = useReactTable({
    data: flatData,
    columns: spanLevelColumns,
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
      createFilterRow(SPAN_FIELDS, {
        trace_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  if (error) {
    return <Alert severity="error">There was an error fetching spans.</Alert>;
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
                    for: "span",
                    id: row.original.span_id,
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
};
