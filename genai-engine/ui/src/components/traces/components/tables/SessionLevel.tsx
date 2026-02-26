import { Alert, Box, Paper, Stack } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";

import { TokenCostTooltip, TokenCountTooltip } from "../../data/common";
import { createSessionLevelColumns } from "../../data/create-session-level-columns";
import { useDrawerTarget } from "../../hooks/useDrawerTarget";
import { useFilterStore } from "../../stores/filter.store";
import { DataContentGate } from "../DataContentGate";

import { SessionsFilterModal } from "./components/SessionsFilterModal";
import { TracesTable } from "./TracesTable";

import { CopyableChip } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useApi } from "@/hooks/useApi";
import { useMRTPagination } from "@/hooks/useMRTPagination";
import { useTask } from "@/hooks/useTask";
import { SessionMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { getFilteredSessions } from "@/services/tracing";
import { formatCurrency, formatDate } from "@/utils/formatters";

interface SessionLevelProps {
  welcomeDismissed: boolean;
}

const DEFAULT_DATA: SessionMetadataResponse[] = [];

export const SessionLevel = ({ welcomeDismissed }: SessionLevelProps) => {
  const api = useApi()!;
  const { task } = useTask();
  const { defaultCurrency } = useDisplaySettings();
  const filters = useFilterStore((state) => state.filters);
  const timeRange = useFilterStore((state) => state.timeRange);

  const { pagination, props } = useMRTPagination({ initialPageSize: FETCH_SIZE });

  const [, setDrawerTarget] = useDrawerTarget();

  const params = useMemo(
    () => ({
      taskId: task?.id ?? "",
      page: pagination.pageIndex,
      pageSize: pagination.pageSize,
      filters,
      timeRange,
    }),
    [task?.id, pagination.pageIndex, pagination.pageSize, filters, timeRange]
  );

  const { data, isLoading, error } = useQuery({
    // eslint-disable-next-line @tanstack/query/exhaustive-deps
    queryKey: queryKeys.sessions.listPaginated(params),
    placeholderData: keepPreviousData,
    queryFn: () => getFilteredSessions(api, params),
  });

  const [sorting] = useState<SortingState>([{ id: "earliest_start_time", desc: true }]);

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

  const displayCurrency = data?.display_currency ?? defaultCurrency;

  const columns = useMemo(
    () =>
      createSessionLevelColumns({
        formatDate,
        formatCurrency: (amount: number) => formatCurrency(amount, displayCurrency),
        onTrack: track,
        Chip: CopyableChip,
        DurationCell: () => null, // Not used in session columns
        TraceContentCell: () => null, // Not used in session columns
        AnnotationCell: () => null, // Not used in session columns
        SpanStatusBadge: () => null, // Not used in session columns
        TypeChip: () => null, // Not used in session columns
        TokenCountTooltip,
        TokenCostTooltip,
      }),
    [displayCurrency]
  );

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
            />
          </>
        )}
      </DataContentGate>
    </Stack>
  );
};
