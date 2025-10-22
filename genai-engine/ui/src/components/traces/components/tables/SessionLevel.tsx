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
import { useQuery } from "@tanstack/react-query";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";

import { sessionLevelColumns } from "../../data/session-level-columns";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { getSessions } from "@/services/tracing";

export const SessionLevel = () => {
  const { task } = useTask();
  const api = useApi();

  const { data, isFetching } = useQuery({
    queryKey: ["sessions", { api, taskId: task?.id }],
    queryFn: () =>
      getSessions(api!, { taskId: task?.id ?? "", page: 0, pageSize: 20 }),
  });

  const flatData = useMemo(() => data?.sessions ?? [], [data]);

  const table = useReactTable({
    data: flatData,
    columns: sessionLevelColumns,
    getCoreRowModel: getCoreRowModel(),
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
