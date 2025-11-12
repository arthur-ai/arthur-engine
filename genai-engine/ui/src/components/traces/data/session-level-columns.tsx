import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { TokenCostTooltip, TokenCountTooltip } from "./common";

import { CopyableChip } from "@/components/common";
import { SessionMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

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
  columnHelper.accessor("earliest_start_time", {
    header: "Earliest Start Time",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.accessor("latest_end_time", {
    header: "Latest End Time",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.accessor("user_id", {
    header: "User ID",
    cell: ({ getValue }) => {
      const label = getValue();
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
