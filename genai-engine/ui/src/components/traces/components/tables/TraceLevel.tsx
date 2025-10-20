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
} from "@mui/material";
import { useThrottler } from "@tanstack/react-pacer";
import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useEffect, useMemo, useRef, useState } from "react";

import { columns } from "../../data/columns";
import { useTracesStore } from "../../store";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { TraceResponse } from "@/lib/api-client/api-client";
import { getFilteredTraces } from "@/services/tracing";

const DEFAULT_DATA: TraceResponse[] = [];
const FETCH_SIZE = 20;

export function TraceLevel() {
  const { task } = useTask();
  const tableContainerRef = useRef(null);

  const api = useApi();
  const [, store] = useTracesStore(() => null);

  const { data, fetchNextPage, isFetching } = useInfiniteQuery({
    queryKey: ["traces", { api, taskId: task?.id }],
    queryFn: ({ pageParam = 0 }) => {
      return getFilteredTraces(api!, {
        taskId: task?.id ?? "",
        page: pageParam as number,
        pageSize: FETCH_SIZE,
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

  const scrollThrottler = useThrottler(
    (containerRef?: HTMLDivElement | null) => {
      if (containerRef) {
        const { scrollHeight, scrollTop, clientHeight } = containerRef;
        const offset = scrollHeight - scrollTop - clientHeight;

        if (offset < 50 && !isFetching && totalDBRowCount >= FETCH_SIZE)
          fetchNextPage();
      }
    },
    {
      wait: 100,
    }
  );

  useEffect(() => {
    scrollThrottler.flush();
    scrollThrottler.maybeExecute(tableContainerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <TableContainer
        component={Paper}
        sx={{ flexGrow: 1 }}
        ref={tableContainerRef}
        onScroll={(e) => {
          scrollThrottler.maybeExecute(e.currentTarget);
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
