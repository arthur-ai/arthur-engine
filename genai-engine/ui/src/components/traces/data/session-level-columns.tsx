import { createColumnHelper } from "@tanstack/react-table";
import dayjs from "dayjs";

import { SessionMetadataResponse } from "@/lib/api-client/api-client";
import { Tooltip } from "@mui/material";
import { CopyableChip } from "@/components/common";
import { getSessionTotals } from "../utils/sessions";
import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";

const columnHelper = createColumnHelper<SessionMetadataResponse>();

export const sessionLevelColumns = [
  columnHelper.accessor("session_id", {
    header: "Session ID",
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
