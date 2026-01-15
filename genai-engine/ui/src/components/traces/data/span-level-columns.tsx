import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Tooltip } from "@mui/material";
import { createMRTColumnHelper } from "material-react-table";

import { DurationCell } from "../components/DurationCell";
import { TraceContentCell } from "../components/TraceContentCell";
import { SpanStatusBadge } from "../components/span-status-badge";
import { isValidStatusCode } from "../components/StatusCode";

import { TokenCostTooltip, TokenCountTooltip } from "./common";

import { CopyableChip } from "@/components/common";
import { TypeChip } from "@/components/common/span/TypeChip";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<SpanMetadataResponse>();

export const spanLevelColumns = [
  columnHelper.accessor("span_kind", {
    header: "Span Kind",
    Cell: ({ cell }) => <TypeChip type={(cell.getValue() as OpenInferenceSpanKind) ?? OpenInferenceSpanKind.AGENT} />,
    size: 140,
  }),
  columnHelper.accessor("status_code", {
    header: "Status",
    Cell: ({ cell }) => {
      const statusCode = cell.getValue();
      return <SpanStatusBadge status={isValidStatusCode(statusCode) ? statusCode : "Unset"} />;
    },
    size: 120,
  }),
  columnHelper.accessor("span_name", {
    header: "Span Name",
    Cell: ({ cell }) => cell.getValue(),
  }),
  columnHelper.accessor("input_content", {
    header: "Input Content",
    Cell: ({ cell, row }) => (
      <span className="w-full">
        <TraceContentCell
          value={cell.getValue()}
          title="Span Input Content"
          traceId={row.original.trace_id ?? undefined}
          spanId={row.original.span_id ?? undefined}
        />
      </span>
    ),
    size: 200,
  }),
  columnHelper.accessor("output_content", {
    header: "Output Content",
    Cell: ({ cell, row }) => (
      <span className="w-full">
        <TraceContentCell
          value={cell.getValue()}
          title="Span Output Content"
          traceId={row.original.trace_id ?? undefined}
          spanId={row.original.span_id ?? undefined}
        />
      </span>
    ),
    size: 200,
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
  columnHelper.accessor("span_id", {
    header: "Span ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();
      return (
        <Tooltip title={label}>
          <span className="w-full">
            <CopyableChip label={label} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),

  columnHelper.accessor("start_time", {
    header: "Start Time",
    Cell: ({ cell }) => formatDate(cell.getValue()),
  }),
  columnHelper.accessor("duration_ms", {
    header: "Latency",
    Cell: ({ cell }) => <DurationCell duration={cell.getValue()} />,
  }),
  columnHelper.accessor("trace_id", {
    header: "Trace ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();
      return (
        <Tooltip title={label}>
          <span className="w-full">
            <CopyableChip label={label} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("session_id", {
    header: "Session ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();

      if (!label) return null;

      return (
        <Tooltip title={label}>
          <span className="w-full">
            <CopyableChip label={label ?? ""} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("user_id", {
    header: "User ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();

      if (!label) return null;

      return (
        <Tooltip title={label}>
          <span className="w-full">
            <CopyableChip label={label ?? ""} sx={{ fontFamily: "monospace" }} />
          </span>
        </Tooltip>
      );
    },
  }),
];
