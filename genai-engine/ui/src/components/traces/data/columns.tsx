import Tooltip from "@mui/material/Tooltip";
import { createColumnHelper } from "@tanstack/react-table";
import dayjs from "dayjs";

import { CopyableChip } from "../../common";

import { TraceMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createColumnHelper<TraceMetadataResponse>();

export const columns = [
  columnHelper.accessor("trace_id", {
    header: "Trace ID",
    size: 100,
    cell: ({ getValue }) => {
      const label = getValue();
      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("span_count", {
    header: "Span Count",
    cell: ({ getValue }) => `${getValue()} spans`,
  }),
  columnHelper.accessor("start_time", {
    header: "Timestamp",
    cell: ({ getValue }) => dayjs(getValue()).format("YYYY-MM-DD HH:mm:ss"),
    sortingFn: "datetime",
  }),
  columnHelper.accessor("duration_ms", {
    header: "Duration",
    cell: ({ getValue }) => `${getValue().toFixed(2)}ms`,
  }),
  columnHelper.accessor("session_id", {
    header: "Session ID",
    cell: ({ getValue }) => {
      const label = getValue();

      if (!label) return null;

      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("user_id", {
    header: "User ID",
    cell: ({ getValue }) => {
      const label = getValue();

      if (!label) return null;

      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
];
