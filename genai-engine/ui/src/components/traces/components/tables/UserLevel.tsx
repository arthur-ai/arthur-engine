import { Alert, Box, TablePagination } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useState } from "react";

import { userLevelColumns } from "../../data/user-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { TracesTable } from "../TracesTable";
import { DataContentGate } from "../DataContentGate";

import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getUsers } from "@/services/tracing";

interface UserLevelProps {
  welcomeDismissed: boolean;
}

export const UserLevel = ({ welcomeDismissed }: UserLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const [, setDrawerTarget] = useDrawerTarget();

  const timeRange = useFilterStore((state) => state.timeRange);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const params = {
    taskId: task?.id ?? "",
    page: pagination.page,
    pageSize: pagination.rowsPerPage,
    filters: [],
    timeRange,
  };

  const { data, isFetching, isPlaceholderData, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getUsers(api, params),
  });

  const [sorting, setSorting] = useState<SortingState>([{ id: "user_id", desc: true }]);

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

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching users.</Alert>
      </Box>
    );
  }

  const hasData = Boolean(data?.users?.length);

  return (
    <Box sx={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", overflow: "auto" }}>
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={false} dataType="users">
        {hasData && (
          <>
            <TracesTable
              table={table}
              loading={isFetching}
              onRowClick={(row) => {
                setDrawerTarget({ target: "user", id: row.original.user_id });
              }}
            />
            <TablePagination
              component="div"
              count={data?.count ?? 0}
              onPageChange={pagination.handlePageChange}
              page={pagination.page}
              rowsPerPage={pagination.rowsPerPage}
              onRowsPerPageChange={pagination.handleRowsPerPageChange}
              rowsPerPageOptions={[10, 25, 50, 100]}
              disabled={isPlaceholderData}
              sx={{
                overflow: "visible",
              }}
            />
          </>
        )}
      </DataContentGate>
    </Box>
  );
};
