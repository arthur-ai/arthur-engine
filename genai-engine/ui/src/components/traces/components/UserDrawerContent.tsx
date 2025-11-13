import { Box, Paper, Skeleton, Stack, TablePagination, Typography } from "@mui/material";
import { useQuery, useSuspenseQuery } from "@tanstack/react-query";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Suspense, useMemo, useRef, useState } from "react";

import { TIME_RANGES, TimeRange } from "../constants";
import { columns } from "../data/columns";
import { TokenCostTooltip, TokenCountTooltip } from "../data/common";
import { sessionLevelColumns } from "../data/session-level-columns";
import { FilterStoreProvider, useFilterStore } from "../stores/filter.store";
import { useTracesHistoryStore } from "../stores/history.store";

import { filterFields } from "./filtering/fields";
import { createFilterRow } from "./filtering/filters-row";
import { IncomingFilter } from "./filtering/mapper";
import { TRACE_FIELDS } from "./filtering/trace-fields";
import { Operators } from "./filtering/types";
import { TimeRangeSelect } from "./TimeRangeSelect";
import { TracesEmptyState } from "./TracesEmptyState";
import { TracesTable } from "./TracesTable";

import { Tabs } from "@/components/ui/Tabs";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { SessionMetadataResponse, TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredSessions, getFilteredTraces, getUser } from "@/services/tracing";

type Props = {
  id: string;
};

export const UserDrawerContent = ({ id }: Props) => {
  const api = useApi()!;
  const { task } = useTask();

  const [timeRange, setTimeRange] = useState<TimeRange>(TIME_RANGES["1 month"]);

  const { data: user } = useSuspenseQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.users.byId(id),
    queryFn: () => getUser(api, { taskId: task?.id ?? "", userId: id }),
  });

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
          backgroundColor: "grey.100",
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
                <TimeRangeSelect value={timeRange} onValueChange={setTimeRange} />
              </Box>
            </Stack>
            <Tabs.Panel value="traces">
              <Suspense fallback={<Skeleton variant="rectangular" height={100} />}>
                <FilterStoreProvider timeRange={timeRange}>
                  <UserTracesTable ids={user.trace_ids} taskId={task?.id ?? ""} />
                </FilterStoreProvider>
              </Suspense>
            </Tabs.Panel>
            <Tabs.Panel value="sessions">
              <Suspense fallback={<Skeleton variant="rectangular" height={100} />}>
                <FilterStoreProvider timeRange={timeRange}>
                  <UserSessionsTable ids={user.session_ids} taskId={task?.id ?? ""} />
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
};

const UserTracesTable = ({ ids, taskId }: UserTableProps) => {
  const api = useApi()!;
  const ref = useRef<HTMLDivElement | null>(null);
  const push = useTracesHistoryStore((state) => state.push);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const combinedFilters: IncomingFilter[] = useMemo(() => [...filters, { name: "trace_ids", operator: Operators.IN, value: ids }], [ids, filters]);

  const params = {
    taskId,
    page: pagination.page,
    pageSize: pagination.rowsPerPage,
    filters: combinedFilters,
    timeRange,
  };

  const traces = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.traces.listPaginated(params),
    queryFn: () => getFilteredTraces(api, params),
  });

  const table = useReactTable({
    data: traces.data?.traces ?? (DEFAULT_DATA as TraceMetadataResponse[]),
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { FiltersRow } = useMemo(() => createFilterRow(USER_FILTERS, {}), []);

  return (
    <Stack gap={1} mt={1}>
      <FiltersRow />
      {traces.data?.count ? (
        <>
          <TracesTable
            table={table}
            ref={ref}
            loading={traces.isFetching}
            onRowClick={(row) => {
              push({
                type: "trace",
                id: row.original.trace_id,
              });
            }}
          />
          <TablePagination
            component="div"
            count={traces.data?.count ?? 0}
            onPageChange={pagination.handlePageChange}
            page={pagination.page}
            rowsPerPage={pagination.rowsPerPage}
            onRowsPerPageChange={pagination.handleRowsPerPageChange}
            disabled={traces.isPlaceholderData}
            sx={{ overflow: "visible" }}
            rowsPerPageOptions={[FETCH_SIZE]}
          />
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

const UserSessionsTable = ({ ids, taskId }: UserTableProps) => {
  const api = useApi()!;
  const ref = useRef<HTMLDivElement | null>(null);
  const push = useTracesHistoryStore((state) => state.push);
  const pagination = useDatasetPagination(FETCH_SIZE);

  const timeRange = useFilterStore((state) => state.timeRange);

  const filters: IncomingFilter[] = useMemo(() => [{ name: "session_ids", operator: Operators.IN, value: ids }], [ids]);

  const params = {
    taskId,
    page: pagination.page,
    pageSize: pagination.rowsPerPage,
    filters,
    timeRange,
  };

  const sessions = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.sessions.listPaginated(params),
    queryFn: () => getFilteredSessions(api, params),
  });

  const table = useReactTable({
    data: sessions.data?.sessions ?? (DEFAULT_DATA as SessionMetadataResponse[]),
    columns: sessionLevelColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  return sessions.data?.count ? (
    <>
      <TracesTable
        table={table}
        ref={ref}
        loading={sessions.isFetching}
        onRowClick={(row) => {
          push({
            type: "session",
            id: row.original.session_id,
          });
        }}
      />
      <TablePagination
        component="div"
        count={sessions.data?.count ?? 0}
        onPageChange={pagination.handlePageChange}
        page={pagination.page}
        rowsPerPage={pagination.rowsPerPage}
        onRowsPerPageChange={pagination.handleRowsPerPageChange}
        disabled={sessions.isPlaceholderData}
        sx={{ overflow: "visible" }}
        rowsPerPageOptions={[FETCH_SIZE]}
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
