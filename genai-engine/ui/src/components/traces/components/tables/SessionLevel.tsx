import {
  keepPreviousData,
  useInfiniteQuery,
  useQuery,
} from "@tanstack/react-query";
import {
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useSelector } from "@xstate/store/react";
import { useMemo, useState } from "react";

import { sessionLevelColumns } from "../../data/session-level-columns";
import { useTableScrollThrottler } from "../../hooks/useTableScrollThrottler";
import { createFilterRow } from "../filtering/filters-row";
import { SESSION_FIELDS } from "../filtering/sessions-fields";
import { useFilterStore } from "../filtering/stores/filter.store";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { FETCH_SIZE } from "@/lib/constants";
import { getSessionsInfiniteQueryOptions } from "@/query-options/sessions";
import { TracesEmptyState } from "../TracesEmptyState";
import { TablePagination, Typography } from "@mui/material";
import { TracesTable } from "../TracesTable";
import { useTracesStore } from "../../store";
import { queryKeys } from "@/lib/queryKeys";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { getFilteredSessions } from "@/services/tracing";

export const SessionLevel = () => {
  const api = useApi()!;
  const { task } = useTask();
  const filters = useSelector(
    useFilterStore(),
    (state) => state.context.filters
  );

  const pagination = useDatasetPagination(FETCH_SIZE);

  const [, store] = useTracesStore(() => null);

  const { data, isFetching, isPlaceholderData } = useQuery({
    queryKey: queryKeys.sessions.listPaginated(
      filters,
      pagination.page,
      pagination.rowsPerPage
    ),
    placeholderData: keepPreviousData,
    queryFn: () =>
      getFilteredSessions(api, {
        taskId: task?.id ?? "",
        page: pagination.page,
        pageSize: pagination.rowsPerPage,
        filters,
      }),
  });

  const [sorting, setSorting] = useState<SortingState>([
    { id: "start_time", desc: true },
  ]);

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

  return (
    <>
      <FiltersRow />
      {data?.sessions?.length ? (
        <>
          <TracesTable
            table={table}
            loading={isFetching}
            onRowClick={(row) => {
              store.send({
                type: "openDrawer",
                for: "session",
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
