import { TextOperators } from "@arthur/shared-components";
import { Search } from "@mui/icons-material";
import AddIcon from "@mui/icons-material/Add";
import LiveTvOutlinedIcon from "@mui/icons-material/LiveTvOutlined";
import {
  Button,
  Paper,
  Table,
  TableCell,
  TableRow,
  TableHead,
  TableContainer,
  TableBody,
  TablePagination,
  Box,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useSuspenseQuery } from "@tanstack/react-query";
import { flexRender, getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { createColumns } from "../../data/columns";
import { continuousEvalsQueryOptions } from "../../hooks/useContinuousEvals";
import { EditFormDialog } from "../edit-form";

import { FilterModal } from "./components/FilterModal";

import { useFilterStore } from "@/components/traces/stores/filter.store";
import { useApi } from "@/hooks/useApi";
import { usePagination } from "@/hooks/usePagination";
import { useTask } from "@/hooks/useTask";

export const Management = () => {
  const { task } = useTask();
  const api = useApi()!;

  const [searchInput, setSearchInput] = useState("");
  const filters = useFilterStore((state) => state.filters);
  const setFilters = useFilterStore((state) => state.setFilters);

  const [continuousEvalId, setContinuousEvalId] = useState<string>();
  const [sorting, setSorting] = useState<SortingState>([{ id: "created_at", desc: true }]);

  const pagination = usePagination();

  const handleSearch = () => {
    if (searchInput.trim()) {
      const existingFilters = filters.filter((f) => f.name !== "name" && f.name !== "llm_eval_name");
      setFilters([
        ...existingFilters,
        {
          name: "name",
          operator: TextOperators.CONTAINS,
          value: searchInput.trim(),
        },
      ]);
    } else {
      // Clear the name filter if search is empty
      setFilters(filters.filter((f) => f.name !== "name" && f.name !== "llm_eval_name"));
    }
  };

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

  return (
    <>
      <Stack
        direction="row"
        spacing={2}
        alignItems="center"
        sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider", backgroundColor: "background.paper" }}
      >
        <TextField
          size="small"
          placeholder="Search by name"
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
      {data.evals.length === 0 ? (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            textAlign: "center",
            py: 8,
          }}
        >
          <LiveTvOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
            No continuous evals yet
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Get started by creating your first continuous eval
          </Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            to={`/tasks/${task?.id}/continuous-evals/new`}
            component={Link}
            size="large"
          >
            Continuous Eval
          </Button>
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
