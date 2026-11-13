import { Tabs, type TimeRange, TimeRangeSelect } from "@arthur/shared-components";
import {
  createSessionLevelColumns,
  createTraceLevelColumns,
  filterFields,
  FilterRow,
  IncomingFilter,
  Operators,
  TokenCostTooltip,
  TokenCountTooltip,
  TRACE_FIELDS,
  TracesEmptyState,
  TracesTable,
  useTraceColumnDependencies,
} from "@arthur/shared-components/traces";
import { Box, Paper, Skeleton, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Suspense, useCallback, useMemo } from "react";

import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useAnnotationCellOptions } from "../../hooks/useTraceAnnotationActions";
import { FilterStoreProvider, useFilterStore } from "../../stores/filter.store";

import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { SessionMetadataResponse, TraceMetadataResponse, TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { trackDynamic } from "@/services/analytics";
import { getFilteredSessions, getFilteredTraces } from "@/services/tracing";

type UserDrawerBodyProps = {
  user: TraceUserMetadataResponse;
  timeRange: TimeRange;
  onTimeRangeChange: (timeRange: TimeRange) => void;
  taskId: string;
  onRowClick?: (target: "trace" | "session", id: string) => void;
};

export const UserDrawerBody = ({ user, timeRange, onTimeRangeChange, taskId, onRowClick }: UserDrawerBodyProps) => {
  // prompt, completion, total
  const tokens = [user.prompt_token_count, user.completion_token_count, user.total_token_count] as const;
  const costs = [user.prompt_token_cost, user.completion_token_cost, user.total_token_cost] as const;

  return (
    <Stack spacing={0} sx={{ height: "100%" }}>
      <Stack
        direction="row"
        sx={{
          justifyContent: "space-between",
          alignItems: "center",
          px: 4,
          py: 2,
          backgroundColor: "action.hover",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack
          direction="column"
          sx={{
            gap: 1,
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
            }}
          >
            User Details
          </Typography>
          <Typography
            variant="h5"
            sx={{
              color: "text.primary",
              fontWeight: "bold",
            }}
          >
            {user.user_id}
          </Typography>
        </Stack>
      </Stack>

      <Stack
        direction="row"
        sx={{
          alignItems: "center",
          gap: 2,
          px: 4,
          py: 2,
        }}
      >
        <TokenCountTooltip prompt={tokens[0] ?? 0} completion={tokens[1] ?? 0} total={tokens[2] ?? 0} />
        <TokenCostTooltip prompt={costs[0] ?? 0} completion={costs[1] ?? 0} total={costs[2] ?? 0} />
      </Stack>

      <Box sx={{ px: 4, py: 2 }}>
        <Paper variant="outlined">
          <Tabs.Root defaultValue="traces">
            <Stack
              direction="row"
              sx={{
                justifyContent: "space-between",
                alignItems: "flex-start",
              }}
            >
              <Tabs.List>
                <Tabs.Tab value="traces">Traces</Tabs.Tab>
                <Tabs.Tab value="sessions">Sessions</Tabs.Tab>

                <Tabs.Indicator />
              </Tabs.List>
              <Box sx={{ ml: "auto", py: 1, mr: 1 }}>
                <TimeRangeSelect value={timeRange} onValueChange={onTimeRangeChange} />
              </Box>
            </Stack>
            <Tabs.Panel value="traces">
              <Suspense fallback={<Skeleton variant="rectangular" height={100} />}>
                <FilterStoreProvider timeRange={timeRange}>
                  <UserTracesTable ids={user.trace_ids} taskId={taskId} onRowClick={onRowClick} />
                </FilterStoreProvider>
              </Suspense>
            </Tabs.Panel>
            <Tabs.Panel value="sessions">
              <Suspense fallback={<Skeleton variant="rectangular" height={100} />}>
                <FilterStoreProvider timeRange={timeRange}>
                  <UserSessionsTable ids={[user.user_id]} taskId={taskId} onRowClick={onRowClick} />
                </FilterStoreProvider>
              </Suspense>
            </Tabs.Panel>
          </Tabs.Root>
        </Paper>
      </Box>
    </Stack>
  );
};

const USER_FILTERS = filterFields(TRACE_FIELDS, ["trace_ids"]);
const DEFAULT_DATA = [] as unknown[];

type UserTableProps = {
  ids: string[];
  taskId: string;
  onRowClick?: (target: "trace" | "session", id: string) => void;
};

const UserTracesTable = ({ ids, taskId, onRowClick }: UserTableProps) => {
  const api = useApi()!;
  const [, setDrawerTarget] = useDrawerTarget();
  const annotationCell = useAnnotationCellOptions();
  const columnDependencies = useTraceColumnDependencies({ onTrack: trackDynamic, annotationCell });

  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const combinedFilters: IncomingFilter[] = useMemo(() => [...filters, { name: "trace_ids", operator: Operators.IN, value: ids }], [ids, filters]);

  const params = {
    taskId,
    page: pagination.pageIndex,
    pageSize: pagination.pageSize,
    filters: combinedFilters,
    timeRange,
  };

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const traces = useQuery({
    queryKey: queryKeys.traces.listPaginated(params),
    queryFn: () => getFilteredTraces(api, params),
  });

  const columns = useMemo(() => createTraceLevelColumns(columnDependencies), [columnDependencies]);

  const setFilters = useFilterStore((state) => state.setFilters);

  const handleFiltersChange = useCallback(
    (newFilters: IncomingFilter[]) => {
      setFilters(newFilters);
    },
    [setFilters]
  );

  const dynamicEnumArgMap = useMemo(
    () => ({
      session_ids: { taskId, api },
      user_ids: { taskId, api },
      span_ids: { taskId, api },
    }),
    [taskId, api]
  );

  const handleRowClick = (row: TraceMetadataResponse) => {
    if (onRowClick) {
      onRowClick("trace", row.trace_id);
    } else {
      setDrawerTarget({ target: "trace", id: row.trace_id });
    }
  };

  return (
    <Stack
      sx={{
        gap: 1,
        mt: 1,
      }}
    >
      <FilterRow
        filters={filters}
        onFiltersChange={handleFiltersChange}
        fieldConfig={USER_FILTERS}
        dynamicEnumArgMap={dynamicEnumArgMap}
        onTrack={trackDynamic}
      />
      {traces.data?.count ? (
        <TracesTable
          data={traces.data?.traces ?? (DEFAULT_DATA as TraceMetadataResponse[])}
          columns={columns}
          rowCount={traces.data?.count ?? 0}
          pagination={pagination}
          onPaginationChange={props.onPaginationChange}
          isLoading={traces.isLoading}
          onRowClick={handleRowClick}
        />
      ) : (
        <TracesEmptyState title="No traces found">
          <Typography
            variant="body1"
            sx={{
              color: "text.secondary",
            }}
          >
            Try adjusting your search query
          </Typography>
        </TracesEmptyState>
      )}
    </Stack>
  );
};

const UserSessionsTable = ({ ids, taskId, onRowClick }: UserTableProps) => {
  const api = useApi()!;
  const [, setDrawerTarget] = useDrawerTarget();
  const columnDependencies = useTraceColumnDependencies({ onTrack: trackDynamic });
  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const timeRange = useFilterStore((state) => state.timeRange);

  const filters: IncomingFilter[] = useMemo(() => [{ name: "user_ids", operator: Operators.IN, value: ids }], [ids]);

  const params = {
    taskId,
    page: pagination.pageIndex,
    pageSize: pagination.pageSize,
    filters,
    timeRange,
  };

  // eslint-disable-next-line @tanstack/query/exhaustive-deps
  const sessions = useQuery({
    queryKey: queryKeys.sessions.listPaginated(params),
    queryFn: () => getFilteredSessions(api, params),
  });

  const columns = useMemo(() => createSessionLevelColumns(columnDependencies), [columnDependencies]);

  const handleRowClick = (row: SessionMetadataResponse) => {
    if (onRowClick) {
      onRowClick("session", row.session_id);
    } else {
      setDrawerTarget({ target: "session", id: row.session_id });
    }
  };

  return sessions.data?.count ? (
    <>
      <TracesTable
        data={sessions.data?.sessions ?? (DEFAULT_DATA as SessionMetadataResponse[])}
        columns={columns}
        rowCount={sessions.data?.count ?? 0}
        pagination={pagination}
        onPaginationChange={props.onPaginationChange}
        isLoading={sessions.isLoading}
        onRowClick={handleRowClick}
      />
    </>
  ) : (
    <TracesEmptyState title="No sessions found">
      <Typography
        variant="body1"
        sx={{
          color: "text.secondary",
        }}
      >
        Try adjusting your search query
      </Typography>
    </TracesEmptyState>
  );
};
