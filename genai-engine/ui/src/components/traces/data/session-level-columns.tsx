import { createColumnHelper } from "@tanstack/react-table";
import dayjs from "dayjs";

import { SessionMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createColumnHelper<SessionMetadataResponse>();

export const sessionLevelColumns = [
  columnHelper.accessor("session_id", {
    header: "Session ID",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("trace_count", {
    header: "Trace Count",
    cell: ({ getValue }) => `${getValue()} traces`,
  }),
  columnHelper.accessor("span_count", {
    header: "Span Count",
    cell: ({ getValue }) => `${getValue()} spans`,
  }),
  columnHelper.accessor("earliest_start_time", {
    header: "Earliest Start Time",
    cell: ({ getValue }) => dayjs(getValue()).format("YYYY-MM-DD HH:mm:ss"),
  }),
  columnHelper.accessor("latest_end_time", {
    header: "Latest End Time",
    cell: ({ getValue }) => dayjs(getValue()).format("YYYY-MM-DD HH:mm:ss"),
  }),
];
