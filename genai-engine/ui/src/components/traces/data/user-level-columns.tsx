import { Tooltip } from "@mui/material";
import { createMRTColumnHelper } from "material-react-table";

import { TokenCostTooltip, TokenCountTooltip } from "./common";

import { CopyableChip } from "@/components/common";
import { TraceUserMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<TraceUserMetadataResponse>();

export const userLevelColumns = [
  columnHelper.accessor("user_id", {
    header: "User ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();
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
    Cell: ({ cell }) => `${cell.getValue()} sessions`,
  }),
  columnHelper.accessor("span_count", {
    header: "Span Count",
    Cell: ({ cell }) => `${cell.getValue()} spans`,
  }),
  columnHelper.accessor("trace_count", {
    header: "Trace Count",
    Cell: ({ cell }) => `${cell.getValue()} traces`,
  }),
  columnHelper.display({
    id: "token-count",
    header: "Token Count",
    Cell: ({ cell }) => {
      const { total_token_count = 0, prompt_token_count = 0, completion_token_count = 0 } = cell.row.original;

      if (!total_token_count) return "-";

      return <TokenCountTooltip prompt={prompt_token_count ?? 0} completion={completion_token_count ?? 0} total={total_token_count} />;
    },
  }),
  columnHelper.display({
    id: "token-cost",
    header: "Token Cost",
    Cell: ({ cell }) => {
      const { total_token_cost = 0, prompt_token_cost = 0, completion_token_cost = 0 } = cell.row.original;

      if (!total_token_cost) return "-";

      return <TokenCostTooltip prompt={prompt_token_cost ?? 0} completion={completion_token_cost ?? 0} total={total_token_cost} />;
    },
  }),
  columnHelper.accessor("earliest_start_time", {
    header: "Earliest Start Time",
    Cell: ({ cell }) => formatDate(cell.getValue()),
  }),
  columnHelper.accessor("latest_end_time", {
    header: "Latest End Time",
    Cell: ({ cell }) => formatDate(cell.getValue()),
  }),
];
