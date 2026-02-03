import { createMRTColumnHelper } from "material-react-table";

import type { ColumnDependencies } from "./column-factory-types";
import { createCountColumn, createDateColumn, createIdColumn, createTokenColumns } from "./column-utils";

import type { TraceUserMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<TraceUserMetadataResponse>();

export const createUserLevelColumns = (deps: ColumnDependencies) => {
  return [
    createIdColumn(columnHelper, "user_id", "User ID", "user", "user", deps, {
      includeMonospace: false,
    }),
    createCountColumn(columnHelper, "session_count", "Session Count", "sessions"),
    createCountColumn(columnHelper, "span_count", "Span Count", "spans"),
    createCountColumn(columnHelper, "trace_count", "Trace Count", "traces"),
    ...createTokenColumns(columnHelper, deps),
    createDateColumn(columnHelper, "earliest_start_time", "Earliest Start Time", deps),
    createDateColumn(columnHelper, "latest_end_time", "Latest End Time", deps),
  ];
};
