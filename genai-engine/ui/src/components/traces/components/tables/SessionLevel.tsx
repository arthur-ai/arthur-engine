import {
  CopyableChip as SharedCopyableChip,
  createSessionLevelColumns,
  type ColumnDependencies as SharedColumnDependencies,
  TracesTable,
} from "@arthur/shared-components";
import { Alert, Box, Paper, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import type { MRT_ColumnDef } from "material-react-table";
import { useCallback, useMemo, useState } from "react";

import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { DataContentGate } from "../DataContentGate";

import { SessionsFilterModal } from "./components/SessionsFilterModal";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { SessionMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getFilteredSessions } from "@/services/tracing";
import { formatDateInTimezone } from "@/utils/formatters";

interface SessionLevelProps {
  welcomeDismissed: boolean;
}

const DEFAULT_DATA: SessionMetadataResponse[] = [];

export const SessionLevel = ({ welcomeDismissed }: SessionLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const { timezone } = useDisplaySettings();
  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [, setDrawerTarget] = useDrawerTarget();

  const [sorting, setSorting] = useState<SortingState>([{ id: "earliest_start_time", desc: true }]);

  const sort: "asc" | "desc" = sorting[0]?.desc === false ? "asc" : "desc";

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters,
      timeRange,
      sort,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, filters, timeRange, sort]
  );

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.sessions.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSessions(api, params),
  });

  const handleRowClick = useCallback(
    (row: { session_id: string }) => {
      track(EVENT_NAMES.TRACING_DRAWER_OPENED, {
        task_id: task?.id ?? "",
        level: "session",
        session_id: row.session_id,
        source: "table",
      });
      setDrawerTarget({ target: "session", id: row.session_id });
    },
    [setDrawerTarget, task?.id]
  );

  const columns = useMemo(() => {
    const deps: SharedColumnDependencies = {
      formatDate: (v) => formatDateInTimezone(v, timezone),
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
    return createSessionLevelColumns(deps) as MRT_ColumnDef<SessionMetadataResponse, unknown>[];
  }, [timezone]);

  // Check if any filters are active
  const hasActiveFilters = useMemo(() => filters.length > 0, [filters]);

  if (error) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">There was an error fetching sessions.</Alert>
      </Box>
    );
  }

  const hasData = Boolean(data?.sessions?.length);

  return (
    <Stack gap={1} overflow="hidden">
      <DataContentGate welcomeDismissed={welcomeDismissed} hasData={hasData} hasActiveFilters={hasActiveFilters} dataType="sessions">
        {/* Filter button */}
        {(hasData || hasActiveFilters || error) && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <SessionsFilterModal />
          </Paper>
        )}

        {hasData && (
          <>
            <TracesTable
              data={data?.sessions ?? DEFAULT_DATA}
              columns={columns}
              rowCount={data?.count ?? 0}
              pagination={pagination}
              onPaginationChange={props.onPaginationChange}
              isLoading={isLoading}
              onRowClick={handleRowClick}
              sorting={sorting}
              onSortingChange={setSorting}
            />
          </>
        )}
      </DataContentGate>
    </Stack>
  );
};
