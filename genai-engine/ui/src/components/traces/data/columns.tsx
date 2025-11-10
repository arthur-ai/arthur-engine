import Tooltip from "@mui/material/Tooltip";
import { createColumnHelper } from "@tanstack/react-table";

import { CopyableChip } from "../../common";

import { TokenCostTooltip, TokenCountTooltip, TruncatedText } from "./common";

import { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate, formatDuration } from "@/utils/formatters";

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
  columnHelper.accessor("input_content", {
    header: "Input Content",
    cell: ({ getValue }) => {
      const value = getValue()?.substring(0, 100);

      if (!value) return "-";

      return <TruncatedText text={value} />;
    },
    size: 200,
  }),
  columnHelper.accessor("output_content", {
    header: "Output Content",
    cell: ({ getValue }) => {
      const value = getValue()?.substring(0, 100);

      if (!value) return "-";

      return <TruncatedText text={value} />;
    },
    size: 200,
  }),
  columnHelper.display({
    id: "token-count",
    header: "Token Count",
    cell: ({ row }) => {
      const { total_token_count = 0, prompt_token_count = 0, completion_token_count = 0 } = row.original;

      if (!total_token_count) return "-";

      return <TokenCountTooltip prompt={prompt_token_count ?? 0} completion={completion_token_count ?? 0} total={total_token_count} />;
    },
  }),
  columnHelper.display({
    id: "token-cost",
    header: "Token Cost",
    cell: ({ row }) => {
      const { total_token_cost = 0, prompt_token_cost = 0, completion_token_cost = 0 } = row.original;

      if (!total_token_cost) return "-";

      return <TokenCostTooltip prompt={prompt_token_cost ?? 0} completion={completion_token_cost ?? 0} total={total_token_cost} />;
    },
  }),
  columnHelper.accessor("span_count", {
    header: "Span Count",
    cell: ({ getValue }) => `${getValue()} spans`,
  }),
  columnHelper.accessor("start_time", {
    header: "Timestamp",
    cell: ({ getValue }) => formatDate(getValue()),
    sortingFn: "datetime",
  }),
  columnHelper.accessor("duration_ms", {
    header: "Duration",
    cell: ({ getValue }) => formatDuration(getValue()),
  }),
  columnHelper.accessor("session_id", {
    header: "Session ID",
    cell: ({ getValue }) => {
      const label = getValue();

      if (!label) return "-";

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

      if (!label) return "-";

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
