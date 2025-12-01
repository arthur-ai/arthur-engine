import AddIcon from "@mui/icons-material/Add";
import { Button, Paper, Stack, Table, Typography, TableCell, TableRow, TableHead, TableContainer, TableBody, TablePagination } from "@mui/material";
import { flexRender, getCoreRowModel, getSortedRowModel, Row, SortingState, useReactTable } from "@tanstack/react-table";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { v4 as uuidv4 } from "uuid";

import { columns, LiveEval } from "./data/columns";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";

const date = new Date();

const data: LiveEval[] = [
  { id: uuidv4(), name: "Live Eval 1", status: "active", createdAt: date.toISOString(), updatedAt: date.toISOString() },
  { id: uuidv4(), name: "Live Eval 2", status: "inactive", createdAt: date.toISOString(), updatedAt: date.toISOString() },
  { id: uuidv4(), name: "Live Eval 3", status: "active", createdAt: date.toISOString(), updatedAt: date.toISOString() },
];

export const LiveEvals = () => {
  const { task } = useTask();
  const navigate = useNavigate();

  const [sorting, setSorting] = useState<SortingState>([{ id: "createdAt", desc: true }]);
  const pagination = useDatasetPagination();

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
  });

  const handleRowClick = (row: Row<LiveEval>) => {
    navigate(`/tasks/${task?.id}/live-evals/${row.original.id}`);
  };

  return (
    <Stack
      sx={{
        height: getContentHeight(),
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack>
          <Typography variant="h5" color="text.primary" fontWeight="bold" mb={0.5}>
            Live Evals
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Live evals are used to monitor and analyze your model's performance in real-time.
          </Typography>
        </Stack>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} to={`/tasks/${task?.id}/live-evals/new`} component={Link}>
          New Live Eval
        </Button>
      </Stack>
      <TableContainer component={Paper} elevation={0} sx={{ flexGrow: 0, flexShrink: 1 }}>
        <Table stickyHeader>
          <TableHead>
            {table.getHeaderGroups().map((header) => (
              <TableRow key={header.id}>
                {header.headers.map((header) => (
                  <TableCell
                    key={header.id}
                    sx={{
                      fontWeight: 600,
                    }}
                  >
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableHead>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} hover onClick={() => handleRowClick(row)} className="cursor-pointer">
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={data.length}
        page={pagination.page}
        onPageChange={pagination.handlePageChange}
        rowsPerPage={pagination.rowsPerPage}
        onRowsPerPageChange={pagination.handleRowsPerPageChange}
        sx={{
          overflow: "visible",
        }}
      />
    </Stack>
  );
};
