import { Alert, Box, TablePagination } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { sessionLevelColumns } from "../../data/session-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { createFilterRow } from "../filtering/filters-row";
import { SESSION_FIELDS } from "../filtering/sessions-fields";
import { TracesTable } from "../TracesTable";
import { WelcomeOrEmptyState } from "../WelcomeOrEmptyState";

import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSessions } from "@/services/tracing";

interface SessionLevelProps {
  welcomeDismissed: boolean;
}

export const SessionLevel = ({ welcomeDismissed }: SessionLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const [, setDrawerTarget] = useDrawerTarget();

  const params = {
    taskId: task?.id ?? "",
    page: pagination.page,
    pageSize: pagination.rowsPerPage,
    filters,
    timeRange,
  };

  const { data, isFetching, isPlaceholderData, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.sessions.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSessions(api, params),
  });

  const [sorting, setSorting] = useState<SortingState>([{ id: "start_time", desc: true }]);

  const table = useReactTable({
    data: data?.sessions ?? [],
    columns: sessionLevelColumns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    rowCount: data?.count ?? 0,
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(SESSION_FIELDS, {
        user_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  // Check if any filters are active
  const hasActiveFilters = filters && Object.keys(filters).length > 0;

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching sessions.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", overflow: "auto" }}>
      {/* Only show FiltersRow if we have sessions or if filters are active */}
      {(data?.sessions?.length || hasActiveFilters) && <FiltersRow />}

      {data?.sessions?.length ? (
        <>
          <TracesTable
            table={table}
            loading={isFetching}
            onRowClick={(row) => {
              setDrawerTarget({ target: "session", id: row.original.session_id });
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
      ) : (
        <WelcomeOrEmptyState hasActiveFilters={hasActiveFilters} welcomeDismissed={welcomeDismissed} dataType="sessions" />
      )}
    </Box>
  );
};
