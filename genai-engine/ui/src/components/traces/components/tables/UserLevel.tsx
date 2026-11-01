import { createUserLevelColumns, TracesTable, useTraceColumnDependencies } from "@arthur/shared-components/traces";
import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import type { MRT_ColumnDef } from "material-react-table";
import { useCallback, useMemo, useState } from "react";

import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { DataContentGate } from "../DataContentGate";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { track, trackDynamic } from "@/services/analytics";
import { getUsers } from "@/services/tracing";

interface UserLevelProps {
  welcomeDismissed: boolean;
}

const DEFAULT_DATA: TraceUserMetadataResponse[] = [];

export const UserLevel = ({ welcomeDismissed }: UserLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const [, setDrawerTarget] = useDrawerTarget();
  const columnDependencies = useTraceColumnDependencies({ onTrack: trackDynamic });

  const timeRange = useFilterStore((state) => state.timeRange);

  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [sorting, setSorting] = useState<SortingState>([{ id: "user_id", desc: true }]);

  const sort: "asc" | "desc" = sorting[0]?.desc === false ? "asc" : "desc";

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters: [],
      timeRange,
      sort,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, timeRange, sort]
  );

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const { data, isLoading, error } = useQuery({
    queryKey: queryKeys.users.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getUsers(api, params),
  });

  const handleRowClick = useCallback(
    (row: { user_id: string }) => {
      track("tracing/drawer_opened", {
        task_id: task?.id ?? "",
        level: "user",
        user_id: row.user_id,
        source: "table",
      });
      setDrawerTarget({ target: "user", id: row.user_id });
    },
    [setDrawerTarget, task?.id]
  );

  const columns = useMemo(
    () => createUserLevelColumns(columnDependencies) as MRT_ColumnDef<TraceUserMetadataResponse, unknown>[],
    [columnDependencies]
  );

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching users.</Alert>
      </Box>
    );
  }

  const hasData = Boolean(data?.users?.length);

  return (
    <Stack
      sx={{
        gap: 1,
        overflow: "hidden",
      }}
    >
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={false} isLoading={isLoading} dataType="users">
        {hasData && (
          <TracesTable
            data={data?.users ?? DEFAULT_DATA}
            columns={columns}
            rowCount={data?.count ?? 0}
            pagination={pagination}
            onPaginationChange={props.onPaginationChange}
            isLoading={isLoading}
            onRowClick={handleRowClick}
            sorting={sorting}
            onSortingChange={setSorting}
          />
        )}
      </DataContentGate>
    </Stack>
  );
};
