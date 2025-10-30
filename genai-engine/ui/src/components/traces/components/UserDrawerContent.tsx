import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { queryKeys } from "@/lib/queryKeys";
import {
  getFilteredTraces,
  getFilteredSessions,
  getUser,
} from "@/services/tracing";
import {
  Box,
  Paper,
  Skeleton,
  Stack,
  TablePagination,
  Typography,
} from "@mui/material";
import {
  useQuery,
  useQueryClient,
  useSuspenseQuery,
} from "@tanstack/react-query";
import { SessionDrawerContent } from "./SessionDrawerContent";
import { Suspense, useMemo, useRef } from "react";
import { TracesTable } from "./TracesTable";
import { getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { IncomingFilter } from "./filtering/mapper";
import { Operators } from "./filtering/types";
import { columns } from "../data/columns";
import { useTracesStore } from "../store";
import { Tabs } from "@/components/ui/Tabs";
import useMeasure from "react-use-measure";
import { motion } from "framer-motion";
import { sessionLevelColumns } from "../data/session-level-columns";
import { createFilterRow } from "./filtering/filters-row";
import { TRACE_FIELDS } from "./filtering/trace-fields";
import { FieldNames, filterFields } from "./filtering/fields";
import {
  FilterStoreProvider,
  useFilterStore,
} from "./filtering/stores/filter.store";
import { useSelector } from "@xstate/store/react";
import {
  SessionMetadataResponse,
  TraceMetadataResponse,
} from "@/lib/api-client/api-client";
import { TracesEmptyState } from "./TracesEmptyState";
import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { FETCH_SIZE } from "@/lib/constants";

type Props = {
  id: string;
};

export const UserDrawerContent = ({ id }: Props) => {
  const api = useApi()!;
  const { task } = useTask();
  const portalRootRef = useRef<HTMLDivElement>(null);

  const { data: user } = useSuspenseQuery({
    queryKey: queryKeys.users.byId(id),
    queryFn: () => getUser(api, { taskId: task?.id ?? "", userId: id }),
  });

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
        ref={portalRootRef}
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

      <Box sx={{ px: 4, py: 2 }}>
        <Paper variant="outlined">
          <Tabs.Root defaultValue="traces">
            <Tabs.List>
              <Tabs.Tab value="traces">Traces</Tabs.Tab>
              <Tabs.Tab value="sessions">Sessions</Tabs.Tab>

              <Tabs.Indicator />
            </Tabs.List>
            <Tabs.Panel value="traces">
              <Suspense
                fallback={<Skeleton variant="rectangular" height={100} />}
              >
                <FilterStoreProvider>
                  <UserTracesTable
                    ids={user.trace_ids}
                    taskId={task?.id ?? ""}
                    portalRootRef={portalRootRef}
                  />
                </FilterStoreProvider>
              </Suspense>
            </Tabs.Panel>
            <Tabs.Panel value="sessions">
              <Suspense
                fallback={<Skeleton variant="rectangular" height={100} />}
              >
                <UserSessionsTable
                  ids={user.session_ids}
                  taskId={task?.id ?? ""}
                  portalRootRef={portalRootRef}
                />
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
  portalRootRef: React.RefObject<HTMLDivElement | null>;
};

const UserTracesTable = ({ ids, taskId, portalRootRef }: UserTableProps) => {
  const api = useApi()!;
  const ref = useRef<HTMLDivElement | null>(null);
  const [, store] = useTracesStore(() => null);

  const pagination = useDatasetPagination(FETCH_SIZE);

  const filters = useSelector(
    useFilterStore(),
    (state) => state.context.filters
  );

  const combinedFilters: IncomingFilter[] = useMemo(
    () => [
      ...filters,
      { name: "trace_ids", operator: Operators.IN, value: ids },
    ],
    [ids, filters]
  );
  const traces = useQuery({
    queryKey: queryKeys.traces.listPaginated(
      combinedFilters,
      pagination.page,
      pagination.rowsPerPage
    ),
    queryFn: () =>
      getFilteredTraces(api, {
        taskId,
        page: pagination.page,
        pageSize: pagination.rowsPerPage,
        filters: combinedFilters,
      }),
  });

  const table = useReactTable({
    data: traces.data?.traces ?? (DEFAULT_DATA as TraceMetadataResponse[]),
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(USER_FILTERS, {}, { portalRoot: portalRootRef.current! }),
    []
  );

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
              store.send({
                type: "openDrawer",
                for: "trace",
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
  const [, store] = useTracesStore(() => null);
  const pagination = useDatasetPagination(FETCH_SIZE);

  const filters: IncomingFilter[] = useMemo(
    () => [{ name: "session_ids", operator: Operators.IN, value: ids }],
    [ids]
  );

  const sessions = useQuery({
    queryKey: queryKeys.sessions.listPaginated(
      filters,
      pagination.page,
      pagination.rowsPerPage
    ),
    queryFn: () =>
      getFilteredSessions(api, {
        taskId,
        page: pagination.page,
        pageSize: pagination.rowsPerPage,
        filters,
      }),
  });

  const table = useReactTable({
    data:
      sessions.data?.sessions ?? (DEFAULT_DATA as SessionMetadataResponse[]),
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
          store.send({
            type: "openDrawer",
            for: "session",
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
