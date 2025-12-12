import { Box, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow } from "@mui/material";
import { useSuspenseQuery } from "@tanstack/react-query";
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { useMemo } from "react";

import { CONTINUOUS_EVAL_RESULT_FIELDS } from "../../data/filter-fields";
import { resultsColumns as columns } from "../../data/results-columns";
import { continuousEvalsResultsQueryOptions } from "../../hooks/useContinuousEvalsResults";

import { createFilterRow } from "@/components/traces/components/filtering/filters-row";
import { TracesEmptyState } from "@/components/traces/components/TracesEmptyState";
import { useFilterStore } from "@/components/traces/stores/filter.store";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

export const Results = () => {
  const api = useApi()!;
  const { task } = useTask();

  const filters = useFilterStore((state) => state.filters);
  const pagination = useDatasetPagination();

  const { data } = useSuspenseQuery(
    continuousEvalsResultsQueryOptions({
      api,
      taskId: task!.id,
      pagination: { page: pagination.page, page_size: pagination.rowsPerPage },
      filters,
    })
  );

  const table = useReactTable({
    data: data.annotations,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { FiltersRow } = useMemo(() => createFilterRow(CONTINUOUS_EVAL_RESULT_FIELDS, {}), []);

  return (
    <>
      <FiltersRow sx={{ border: "none" }} getNameLabel={getFieldLabel} />
      {data.annotations.length === 0 ? (
        <Box sx={{ p: 2 }}>
          <TracesEmptyState title="No annotations found" />
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
    </>
  );
};

const getFieldLabel = (name: string) => {
  return (
    {
      id: "Continuous Eval ID",
      trace_id: "Trace ID",
      annotation_score: "Annotation Score",
      run_status: "Run Status",
      created_at: "Created At",
    }[name] ?? name
  );
};
