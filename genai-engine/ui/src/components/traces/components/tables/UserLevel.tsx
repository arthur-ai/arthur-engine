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
import { useMemo, useState } from "react";

import { userLevelColumns } from "../../data/user-level-columns";
import { useTableScrollThrottler } from "../../hooks/useTableScrollThrottler";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { FETCH_SIZE } from "@/lib/constants";
import { getUsersInfiniteQueryOptions } from "@/query-options/users";
import { Alert } from "@mui/material";

export const UserLevel = () => {
  const api = useApi()!;
  const { task } = useTask();

  const { data, isFetching, fetchNextPage, error } = useInfiniteQuery({
    ...getUsersInfiniteQueryOptions({
      api,
      taskId: task?.id ?? "",
    }),
  });

  const [sorting, setSorting] = useState<SortingState>([
    { id: "user_id", desc: true },
  ]);

  const flatData = useMemo(
    () => data?.pages?.flatMap((page) => page.users) ?? [],
    [data]
  );

  const totalDBRowCount = data?.pages?.[0]?.count ?? 0;

  const table = useReactTable({
    data: flatData,
    columns: userLevelColumns,
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

  if (error) {
    return <Alert severity="error">There was an error fetching users.</Alert>;
  }

  return (
    <>
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
                          {
                            id: header.column.id,
                            desc: !(prev[0]?.desc ?? true),
                          },
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
              <TableRow key={row.id} hover onClick={() => {}}>
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
