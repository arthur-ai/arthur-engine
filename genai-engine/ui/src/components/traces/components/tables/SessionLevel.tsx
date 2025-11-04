import { Alert, TablePagination, Typography } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { sessionLevelColumns } from "../../data/session-level-columns";
import { useFilterStore } from "../../stores/filter.store";
import { useTracesHistoryStore } from "../../stores/history.store";
import { createFilterRow } from "../filtering/filters-row";
import { SESSION_FIELDS } from "../filtering/sessions-fields";
import { TracesEmptyState } from "../TracesEmptyState";
import { TracesTable } from "../TracesTable";

import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSessions } from "@/services/tracing";

export const SessionLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const push = useTracesHistoryStore((state) => state.push);

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

  if (error) {
    return <Alert severity="error">There was an error fetching sessions.</Alert>;
  }

  return (
    <>
      <FiltersRow />
      {data?.sessions?.length ? (
        <>
          <TracesTable
            table={table}
            loading={isFetching}
            onRowClick={(row) => {
              push({
                type: "session",
                id: row.original.session_id,
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
        <TracesEmptyState title="No sessions found">
          <Typography variant="body1" color="text.secondary">
            Try adjusting your search query
          </Typography>
        </TracesEmptyState>
      )}
    </>
  );
};
