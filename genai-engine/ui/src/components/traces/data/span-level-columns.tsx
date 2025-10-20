import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";
import dayjs from "dayjs";

import { CopyableChip } from "@/components/common";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";


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
    cell: ({ getValue }) => dayjs(getValue()).format("YYYY-MM-DD HH:mm:ss"),
  }),
  columnHelper.accessor("duration_ms", {
    header: "Duration",
    cell: ({ getValue }) => `${getValue()}ms`,
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
];