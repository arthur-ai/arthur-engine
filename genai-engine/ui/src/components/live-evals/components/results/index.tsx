import { Box, Button, Dialog, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, TextField } from "@mui/material";
import { Search } from "@mui/icons-material";
import { useSuspenseQuery } from "@tanstack/react-query";
import { flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { parseAsString, parseAsStringEnum, useQueryState } from "nuqs";
import { useMemo, useState } from "react";

import { createColumns } from "../../data/results-columns";
import { continuousEvalsResultsQueryOptions } from "../../hooks/useContinuousEvalsResults";

import { Details } from "./components/details";
import { FilterModal } from "./components/FilterModal";

import { TracesEmptyState } from "@/components/traces/components/TracesEmptyState";
import { TextOperators } from "@/components/traces/components/filtering/types";
import { useFilterStore } from "@/components/traces/stores/filter.store";
import { useApi } from "@/hooks/useApi";
import { usePagination } from "@/hooks/usePagination";
import { useTask } from "@/hooks/useTask";

export const Results = () => {
  const api = useApi()!;
  const { task } = useTask();

  const [annotationId, setAnnotationId] = useQueryState("id", parseAsString.withDefault(""));
  const [action, setAction] = useQueryState("action", parseAsStringEnum(["rerun"]));

  const [searchInput, setSearchInput] = useState("");
  const filters = useFilterStore((state) => state.filters);
  const setFilters = useFilterStore((state) => state.setFilters);
  const pagination = usePagination();

  const handleSearch = () => {
    if (searchInput.trim()) {
      const existingFilters = filters.filter((f) => f.name !== "eval_name");
      setFilters([
        ...existingFilters,
        {
          name: "eval_name",
          operator: TextOperators.CONTAINS,
          value: searchInput.trim(),
        },
      ]);
    } else {
      // Clear the eval_name filter if search is empty
      setFilters(filters.filter((f) => f.name !== "eval_name"));
    }
  };

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
    columns: useMemo(() => createColumns({ onView: (annotationId) => setAnnotationId(annotationId) }), [setAnnotationId]),
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "background.paper" }}>
        <TextField
          size="small"
          placeholder="Search by eval name"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSearch();
            }
          }}
          sx={{ width: 300 }}
        />
        <Button variant="outlined" startIcon={<Search />} onClick={handleSearch}>
          Search
        </Button>
        <FilterModal />
      </Stack>
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
                  <TableRow key={row.id} hover onClick={() => setAnnotationId(row.original.id)} sx={{ cursor: "pointer" }}>
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

      <Dialog open={!!annotationId} onClose={() => setAnnotationId("")} maxWidth="xl" fullWidth>
        <Details
          annotationId={annotationId || undefined}
          onClose={() => setAnnotationId("")}
          onRerunComplete={() => setAction(null)}
          rerunOnMount={action === "rerun"}
        />
      </Dialog>
    </>
  );
};
