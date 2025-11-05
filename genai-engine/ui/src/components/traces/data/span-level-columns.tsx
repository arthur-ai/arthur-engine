import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { CopyableChip } from "@/components/common";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

const columnHelper = createColumnHelper<SpanMetadataResponse>();

export const spanLevelColumns = [
  columnHelper.accessor("span_id", {
    header: "Span ID",
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
  columnHelper.accessor("span_name", {
    header: "Span Name",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("start_time", {
    header: "Start Time",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.accessor("duration_ms", {
    header: "Duration",
    cell: ({ getValue }) => `${getValue().toFixed(2)}ms`,
  }),
  columnHelper.accessor("trace_id", {
    header: "Trace ID",
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
  columnHelper.accessor("session_id", {
    header: "Session ID",
    cell: ({ getValue }) => {
      const label = getValue();
      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip
              label={label ?? ""}
              sx={{ fontFamily: "monospace" }}
            />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("user_id", {
    header: "User ID",
    cell: ({ getValue }) => {
      const label = getValue();
      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip
              label={label ?? ""}
              sx={{ fontFamily: "monospace" }}
            />
          </span>
        </Tooltip>
      );
    },
  }),
];
