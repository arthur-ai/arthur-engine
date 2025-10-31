import { TablePagination, Typography } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo, useState } from "react";

import { columns } from "../../data/columns";
import { useFilterStore } from "../../stores/filter.store";
import { useTracesHistoryStore } from "../../stores/history.store";
import { createFilterRow } from "../filtering/filters-row";
import { TRACE_FIELDS } from "../filtering/trace-fields";

import { useDatasetPagination } from "@/hooks/datasets/useDatasetPagination";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { FETCH_SIZE } from "@/lib/constants";
import { queryKeys } from "@/lib/queryKeys";
import { getFilteredTraces } from "@/services/tracing";
import { TracesEmptyState } from "../TracesEmptyState";
import { TracesTable } from "../TracesTable";

const DEFAULT_DATA: TraceMetadataResponse[] = [];

export function TraceLevel() {
  const { task } = useTask();
  const pagination = useDatasetPagination(FETCH_SIZE);

  const push = useTracesHistoryStore((state) => state.push);

  const filters = useFilterStore((state) => state.filters);

  const api = useApi()!;

  const { data, isFetching } = useQuery({
    queryKey: queryKeys.traces.listPaginated(filters, 0, FETCH_SIZE),
    placeholderData: keepPreviousData,
    queryFn: () =>
      getFilteredTraces(api, {
        taskId: task?.id ?? "",
        page: 0,
        pageSize: FETCH_SIZE,
        filters,
      }),
  });

  const [sorting, setSorting] = useState<SortingState>([
    { id: "start_time", desc: true },
  ]);

  const table = useReactTable({
    data: data?.traces ?? DEFAULT_DATA, // Use test data to verify scrolling
    columns,
    getCoreRowModel: getCoreRowModel(),
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
  });

  const { FiltersRow } = useMemo(
    () =>
      createFilterRow(TRACE_FIELDS, {
        trace_ids: { taskId: task?.id ?? "", api },
      }),
    [task?.id, api]
  );

  return (
    <>
      <FiltersRow />
      {data?.traces?.length ? (
        <>
          <TracesTable
            table={table}
            loading={isFetching}
            onRowClick={(row) => {
              push({
                type: "trace",
                id: row.original.trace_id,
              });
            }}
          />
          <TablePagination
            component="div"
            count={data?.count ?? 0}
            onPageChange={pagination.handlePageChange}
            page={pagination.page}
            rowsPerPage={pagination.rowsPerPage}
            sx={{
              overflow: "visible",
            }}
          />
        </>
      ) : (
        <TracesEmptyState title="No traces found">
          <Typography variant="body1" color="text.secondary">
            Try adjusting your search query
          </Typography>
        </TracesEmptyState>
      )}
    </>
  );
}
