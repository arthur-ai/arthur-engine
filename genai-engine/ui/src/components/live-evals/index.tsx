import AddIcon from "@mui/icons-material/Add";
import {
  Button,
  Paper,
  Stack,
  Table,
  Typography,
  TableCell,
  TableRow,
  TableHead,
  TableContainer,
  TableBody,
  TablePagination,
  Skeleton,
  Box,
} from "@mui/material";
import { flexRender, getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { TracesEmptyState } from "../traces/components/TracesEmptyState";

import { EditFormDialog } from "./components/edit-form";
import { createColumns } from "./data/columns";
import { useContinuousEvals } from "./hooks/useContinuousEvals";

import { getContentHeight } from "@/constants/layout";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useTask } from "@/hooks/useTask";
import { ContinuousEvalResponse } from "@/lib/api-client/api-client";

const DEFAULT_DATA: ContinuousEvalResponse[] = [];

export const LiveEvals = () => {
  const { task } = useTask();

  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);
  const [continuousEvalId, setContinuousEvalId] = useState<string>();

  const pagination = useDatasetPagination();

  const { data, isLoading } = useContinuousEvals();

  const table = useReactTable({
    data: data?.evals ?? DEFAULT_DATA,
    columns: useMemo(
      () =>
        createColumns({
          onEdit: (id) => setContinuousEvalId(id),
        }),
      [setContinuousEvalId]
    ),
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return <LiveEvalsSkeleton />;
  }

  return (
    <>
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
              Continuous Evals
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Continuous evals are used to monitor and analyze your model's performance in real-time.
            </Typography>
          </Stack>
          <Button variant="contained" color="primary" startIcon={<AddIcon />} to={`/tasks/${task?.id}/continuous-evals/new`} component={Link}>
            New Continuous Eval
          </Button>
        </Stack>
        {data?.evals.length === 0 ? (
          <Box sx={{ p: 2 }}>
            <TracesEmptyState title="No continuous evals found">
              <Button
                disableElevation
                variant="contained"
                color="primary"
                startIcon={<AddIcon />}
                to={`/tasks/${task?.id}/continuous-evals/new`}
                component={Link}
              >
                Create Continuous Eval
              </Button>
            </TracesEmptyState>
          </Box>
        ) : (
          <>
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
                    <TableRow key={row.id} hover>
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
              count={data?.count ?? 0}
              page={pagination.page}
              onPageChange={pagination.handlePageChange}
              rowsPerPage={pagination.rowsPerPage}
              onRowsPerPageChange={pagination.handleRowsPerPageChange}
              sx={{
                overflow: "visible",
              }}
            />
          </>
        )}
      </Stack>

      <EditFormDialog continuousEvalId={continuousEvalId} onClose={() => setContinuousEvalId(undefined)} />
    </>
  );
};

export const LiveEvalsSkeleton = () => {
  return (
    <Stack sx={{ height: getContentHeight() }}>
      {/* Header section */}
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
          <Skeleton variant="text" width={180} height={32} sx={{ mb: 0.5 }} />
          <Skeleton variant="text" width={480} height={20} />
        </Stack>
        <Skeleton variant="rounded" width={180} height={36} />
      </Stack>
      <Box sx={{ p: 3, flex: 1 }}>
        <Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />
      </Box>
    </Stack>
  );
};
