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
import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";

import { spanLevelColumns } from "../../data/span-level-columns";
import { useTracesStore } from "../../store";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { getFilteredSpans } from "@/services/tracing";

export const SpanLevel = () => {
  const api = useApi();
  const { task } = useTask();
  const [, store] = useTracesStore(() => null);

  const { data, isFetching } = useInfiniteQuery({
    queryKey: ["spans", { api, taskId: task?.id }],
    queryFn: ({ pageParam = 0 }) => {
      return getFilteredSpans(api!, {
        taskId: task?.id ?? "",
        page: pageParam as number,
        pageSize: 20,
      });
    },
    initialPageParam: 0,
    getNextPageParam: (_, __, lastPageParam = 0) => {
      return lastPageParam + 1;
    },
    refetchOnWindowFocus: false,
    placeholderData: keepPreviousData,
  });

  const flatData = useMemo(
    () => data?.pages?.flatMap((page) => page.spans) ?? [],
    [data]
  );

  const table = useReactTable({
    data: flatData,
    columns: spanLevelColumns,
    getCoreRowModel: getCoreRowModel(),
    debugTable: true,
    debugHeaders: true,
    debugColumns: true,
  });

  return (
    <>
      <TableContainer component={Paper} sx={{ flexGrow: 1 }}>
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
