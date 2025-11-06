import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { TokenCostTooltip, TokenCountTooltip } from "./common";

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
  columnHelper.accessor("span_kind", {
    header: "Span Kind",
    cell: ({ getValue }) => getValue(),
  }),
  columnHelper.accessor("input_content", {
    header: "Input Content",
  }),
  columnHelper.accessor("output_content", {
    header: "Output Content",
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

      if (!label) return null;

      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip label={label ?? ""} sx={{ fontFamily: "monospace" }} />
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
            <CopyableChip label={label ?? ""} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
];
