import { Alert, Box, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";

import {
  CopyableChip as SharedCopyableChip,
  createUserLevelColumns,
  type ColumnDependencies as SharedColumnDependencies,
  TracesTable,
} from "@arthur/shared-components";
import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { DataContentGate } from "../DataContentGate";

import type { MRT_ColumnDef } from "material-react-table";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getUsers } from "@/services/tracing";
import { formatDate } from "@/utils/formatters";

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

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getUsers(api, params),
  });

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

  const columns = useMemo(() => {
    const deps: SharedColumnDependencies = {
      formatDate,
      formatCurrency: () => "",
      onTrack: track,
      Chip: SharedCopyableChip,
      DurationCell: () => null,
      TraceContentCell: () => null,
      AnnotationCell: () => null,
      SpanStatusBadge: () => null,
      TypeChip: () => null,
      TokenCountTooltip,
      TokenCostTooltip,
    };
    return createUserLevelColumns(deps) as MRT_ColumnDef<TraceUserMetadataResponse, any>[];
  }, []);

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
