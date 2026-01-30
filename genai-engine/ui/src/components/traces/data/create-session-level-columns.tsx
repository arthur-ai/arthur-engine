import { createMRTColumnHelper } from "material-react-table";

import type { ColumnDependencies } from "./column-factory-types";
import { createCountColumn, createDateColumn, createIdColumn, createTokenColumns } from "./column-utils";

import type { SessionMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<SessionMetadataResponse>();

export const createSessionLevelColumns = (deps: ColumnDependencies) => {
  return [
    createIdColumn(columnHelper, "session_id", "Session ID", "session", "session", deps),
    createCountColumn(columnHelper, "trace_count", "Trace Count", "traces"),
    createCountColumn(columnHelper, "span_count", "Span Count", "spans"),
    ...createTokenColumns(columnHelper, deps),
    createDateColumn(columnHelper, "earliest_start_time", "Earliest Start Time", deps),
    createDateColumn(columnHelper, "latest_end_time", "Latest End Time", deps),
    createIdColumn(columnHelper, "user_id", "User ID", "session", "user", deps),
  ];
};
