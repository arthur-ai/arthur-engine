import { Alert, Box } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { MaterialReactTable } from "material-react-table";
import { useState } from "react";

import { userLevelColumns } from "../../data/user-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useTable } from "../../hooks/useTable";
import { useFilterStore } from "../../stores/filter.store";
import { DataContentGate } from "../DataContentGate";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
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

  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const params = {
    taskId: task?.id ?? "",
    page: pagination.pageIndex,
    pageSize: pagination.pageSize,
    filters: [],
    timeRange,
  };

  const { data, isLoading, isFetching, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getUsers(api, params),
  });

  const [sorting] = useState<SortingState>([{ id: "user_id", desc: true }]);

  const table = useTable({
    data: data?.users ?? [],
    columns: userLevelColumns,
    pagination: { state: pagination, onChange: props.onPaginationChange },
    state: {
      sorting,
      isLoading,
      showProgressBars: isFetching,
    },
    onRowClick: (row) => setDrawerTarget({ target: "user", id: row.user_id }),
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
        {hasData && <MaterialReactTable table={table} />}
      </DataContentGate>
    </Box>
  );
};
