import Box from "@mui/material/Box";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import Typography from "@mui/material/Typography";
import { useThrottler } from "@tanstack/react-pacer";
import { keepPreviousData, useInfiniteQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import React, { useEffect, useMemo, useRef, useState } from "react";

import { TraceDrawer } from "./traces/components/TraceDrawer";
import { columns } from "./traces/data/columns";
import { useTracesStore } from "./traces/store";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { TraceResponse } from "@/lib/api-client/api-client";
import { getFilteredTraces } from "@/services/tracing";

const DEFAULT_DATA: TraceResponse[] = [];
const FETCH_SIZE = 20;

export const TracesView: React.FC = () => {
  const api = useApi();
  const { task } = useTask();
  const tableContainerRef = useRef(null);

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
  const totalFetched = flatData.length;

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
      console.log("scrollThrottler");
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

  useEffect(() => {
    console.log({ sorting });
  }, [sorting]);

  return (
    <>
      <Box
        sx={{
          maxHeight: "calc(100vh - 88px)",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          p: 2,
          gap: 2,
        }}
      >
        <Paper
          component={Stack}
          elevation={0}
          direction="row"
          spacing={2}
          justifyContent="flex-end"
          sx={{
            py: 1,
            px: 2,
            borderRadius: 1,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ fontFamily: "monospace" }}
          >
            {totalFetched} rows fetched
          </Typography>
        </Paper>
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
                      type: "selectTrace",
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
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
      <TraceDrawer />
    </>
  );
};
