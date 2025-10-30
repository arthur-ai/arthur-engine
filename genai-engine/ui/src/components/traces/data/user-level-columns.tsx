import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { CopyableChip } from "@/components/common";
import { TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/date";

const columnHelper = createColumnHelper<TraceUserMetadataResponse>();

export const userLevelColumns = [
  columnHelper.accessor("user_id", {
    header: "User ID",
    cell: ({ getValue }) => {
      const label = getValue();
      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("session_count", {
    header: "Session Count",
    cell: ({ getValue }) => `${getValue()} sessions`,
  }),
  columnHelper.accessor("span_count", {
    header: "Span Count",
    cell: ({ getValue }) => `${getValue()} spans`,
  }),
  columnHelper.accessor("trace_count", {
    header: "Trace Count",
    cell: ({ getValue }) => `${getValue()} traces`,
  }),
  columnHelper.accessor("earliest_start_time", {
    header: "Earliest Start Time",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.accessor("latest_end_time", {
    header: "Latest End Time",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
];
