import {
  createSessionLevelColumns,
  createTraceLevelColumns,
  FilterRow,
  Operators,
  TimeRangeSelect,
  TracesEmptyState,
  TracesTable,
} from "@arthur/shared-components";
import { Box, Paper, Skeleton, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import type { MRT_ColumnDef } from "material-react-table";
import { Suspense, useCallback, useMemo } from "react";

import type { TimeRange } from "../../constants";
import { BucketProvider } from "../../context/bucket-context";
import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { FilterStoreProvider, useFilterStore } from "../../stores/filter.store";
import { buildThresholdsFromSample } from "../../utils/duration";
import { filterFields } from "../filtering/fields";
import { IncomingFilter } from "../filtering/mapper";
import { TRACE_FIELDS } from "../filtering/trace-fields";

import { CopyableChip } from "@/components/common";
import { Tabs } from "@/components/ui/Tabs";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { SessionMetadataResponse, TraceMetadataResponse, TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { track } from "@/services/amplitude";
import { getFilteredSessions, getFilteredTraces } from "@/services/tracing";
import { formatDate } from "@/utils/formatters";

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
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 4,
          py: 2,
          backgroundColor: "action.hover",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="column" gap={1}>
          <Typography variant="body2" color="text.secondary">
            User Details
          </Typography>
          <Typography variant="h5" color="text.primary" fontWeight="bold">
            {user.user_id}
          </Typography>
        </Stack>
      </Stack>

      <Stack direction="row" alignItems="center" gap={2} sx={{ px: 4, py: 2 }}>
        <TokenCountTooltip prompt={tokens[0] ?? 0} completion={tokens[1] ?? 0} total={tokens[2] ?? 0} />
        <TokenCostTooltip prompt={costs[0] ?? 0} completion={costs[1] ?? 0} total={costs[2] ?? 0} />
      </Stack>

      <Box sx={{ px: 4, py: 2 }}>
        <Paper variant="outlined">
          <Tabs.Root defaultValue="traces">
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
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

  const traces = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.traces.listPaginated(params),
    queryFn: () => getFilteredTraces(api, params),
  });

  const columns = useMemo(
    () =>
      createTraceLevelColumns({
        formatDate,
        formatCurrency: () => "",
        onTrack: track,
        Chip: CopyableChip,
        DurationCell: () => null,
        TraceContentCell: () => null,
        AnnotationCell: () => null,
        SpanStatusBadge: () => null,
        TypeChip: () => null,
        TokenCountTooltip,
        TokenCostTooltip,
      }) as unknown as MRT_ColumnDef<TraceMetadataResponse, unknown>[],
    []
  );

  const thresholds = useMemo(() => buildThresholdsFromSample(traces.data?.traces.map((trace) => trace.duration_ms) ?? []), [traces.data?.traces]);

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
    <Stack gap={1} mt={1}>
      <FilterRow
        filters={filters}
        onFiltersChange={handleFiltersChange}
        fieldConfig={USER_FILTERS}
        dynamicEnumArgMap={dynamicEnumArgMap}
        onTrack={track}
      />
      {traces.data?.count ? (
        <>
          <BucketProvider thresholds={thresholds}>
            <TracesTable
              data={traces.data?.traces ?? (DEFAULT_DATA as TraceMetadataResponse[])}
              columns={columns}
              rowCount={traces.data?.count ?? 0}
              pagination={pagination}
              onPaginationChange={props.onPaginationChange}
              isLoading={traces.isLoading}
              onRowClick={handleRowClick}
            />
          </BucketProvider>
        </>
      ) : (
        <TracesEmptyState title="No traces found">
          <Typography variant="body1" color="text.secondary">
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

  const sessions = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.sessions.listPaginated(params),
    queryFn: () => getFilteredSessions(api, params),
  });

  const columns = useMemo(
    () =>
      createSessionLevelColumns({
        formatDate,
        formatCurrency: () => "",
        onTrack: track,
        Chip: CopyableChip,
        DurationCell: () => null,
        TraceContentCell: () => null,
        AnnotationCell: () => null,
        SpanStatusBadge: () => null,
        TypeChip: () => null,
        TokenCountTooltip,
        TokenCostTooltip,
      }) as unknown as MRT_ColumnDef<SessionMetadataResponse, unknown>[],
    []
  );

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
      <Typography variant="body1" color="text.secondary">
        Try adjusting your search query
      </Typography>
    </TracesEmptyState>
  );
};
