import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { MaterialReactTable } from "material-react-table";
import { useCallback, useMemo, useState } from "react";

import { userLevelColumns } from "../../data/user-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useTable } from "../../hooks/useTable";
import { useFilterStore } from "../../stores/filter.store";
import { DataContentGate } from "../DataContentGate";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getUsers } from "@/services/tracing";

interface UserLevelProps {
  welcomeDismissed: boolean;
}

const DEFAULT_DATA: TraceUserMetadataResponse[] = [];

export const UserLevel = ({ welcomeDismissed }: UserLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const [, setDrawerTarget] = useDrawerTarget();

  const timeRange = useFilterStore((state) => state.timeRange);

  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters: [],
      timeRange,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, timeRange]
  );

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getUsers(api, params),
  });

  const [sorting] = useState<SortingState>([{ id: "user_id", desc: true }]);

  const handleRowClick = useCallback(
    (row: { user_id: string }) => {
      track(EVENT_NAMES.TRACING_DRAWER_OPENED, {
        task_id: task?.id ?? "",
        level: "user",
        user_id: row.user_id,
        source: "table",
      });
      setDrawerTarget({ target: "user", id: row.user_id });
    },
    [setDrawerTarget, task?.id]
  );

  const table = useTable({
    data: data?.users ?? DEFAULT_DATA,
    columns: userLevelColumns,
    pagination: { state: pagination, onChange: props.onPaginationChange, rowCount: data?.count ?? 0 },
    state: {
      sorting,
      isLoading,
    },
    onRowClick: handleRowClick,
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
    <Stack gap={1} overflow="hidden">
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={false} dataType="users">
        {hasData && <MaterialReactTable table={table} />}
      </DataContentGate>
    </Stack>
  );
};
