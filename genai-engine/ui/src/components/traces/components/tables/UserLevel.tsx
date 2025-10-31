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
import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";
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
import { TracesEmptyState } from "../TracesEmptyState";
import { TablePagination, Typography } from "@mui/material";
import { TracesTable } from "../TracesTable";
import { useTracesHistoryStore } from "../../stores/history.store";
import { queryKeys } from "@/lib/queryKeys";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { getUsers } from "@/services/tracing";

export const UserLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const push = useTracesHistoryStore((state) => state.push);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const { data, isFetching, isPlaceholderData } = useQuery({
    queryKey: queryKeys.users.listPaginated(
      pagination.page,
      pagination.rowsPerPage
    ),
    placeholderData: keepPreviousData,
    queryFn: () =>
      getUsers(api, {
        taskId: task?.id ?? "",
        page: pagination.page,
        pageSize: pagination.rowsPerPage,
        filters: [],
      }),
  });

  const [sorting, setSorting] = useState<SortingState>([
    { id: "user_id", desc: true },
  ]);

  const table = useReactTable({
    data: data?.users ?? [],
    columns: userLevelColumns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    rowCount: data?.count ?? 0,
  });

  return (
    <>
      {data?.users?.length ? (
        <>
          <TracesTable
            table={table}
            loading={isFetching}
            onRowClick={(row) => {
              push({
                type: "user",
                id: row.original.user_id,
              });
            }}
          />
          <TablePagination
            component="div"
            count={data?.count ?? 0}
            onPageChange={pagination.handlePageChange}
            page={pagination.page}
            rowsPerPage={pagination.rowsPerPage}
            onRowsPerPageChange={pagination.handleRowsPerPageChange}
            disabled={isPlaceholderData}
            sx={{
              overflow: "visible",
            }}
          />
        </>
      ) : (
        <TracesEmptyState title="No users found">
          <Typography variant="body1" color="text.secondary">
            Try adjusting your search query
          </Typography>
        </TracesEmptyState>
      )}
    </>
  );
};
