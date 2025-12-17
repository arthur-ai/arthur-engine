import AddIcon from "@mui/icons-material/Add";
import { Button, Paper, Table, TableCell, TableRow, TableHead, TableContainer, TableBody, TablePagination, Box } from "@mui/material";
import { useSuspenseQuery } from "@tanstack/react-query";
import { flexRender, getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { createColumns } from "../../data/columns";
import { CONTINUOUS_EVAL_FILTER_FIELDS } from "../../data/filter-fields";
import { continuousEvalsQueryOptions } from "../../hooks/useContinuousEvals";
import { EditFormDialog } from "../edit-form";

import { createFilterRow } from "@/components/traces/components/filtering/filters-row";
import { TracesEmptyState } from "@/components/traces/components/TracesEmptyState";
import { useFilterStore } from "@/components/traces/stores/filter.store";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

export const Management = () => {
  const { task } = useTask();
  const api = useApi()!;

  const filters = useFilterStore((state) => state.filters);

  const [continuousEvalId, setContinuousEvalId] = useState<string>();
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);

  const pagination = useDatasetPagination();

  const { data } = useSuspenseQuery(
    continuousEvalsQueryOptions({
      api,
      taskId: task!.id,
      pagination: { page: pagination.page, page_size: pagination.rowsPerPage },
      filters,
    })
  );

  const table = useReactTable({
    data: data.evals,
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

  const { FiltersRow } = useMemo(() => createFilterRow(CONTINUOUS_EVAL_FILTER_FIELDS, {}), []);

  return (
    <>
      <FiltersRow sx={{ border: "none" }} getNameLabel={getFieldLabel} />
      {data.evals.length === 0 ? (
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
            count={data.count}
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

      <EditFormDialog continuousEvalId={continuousEvalId} onClose={() => setContinuousEvalId(undefined)} />
    </>
  );
};

const getFieldLabel = (name: string) => {
  return (
    {
      name: "Name",
      llm_eval_name: "Evaluator Name",
      created_at: "Created At",
    }[name] ?? name
  );
};
