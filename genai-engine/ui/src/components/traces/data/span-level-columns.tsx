import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { Tooltip } from "@mui/material";
import { createColumnHelper } from "@tanstack/react-table";

import { isValidStatusCode, StatusCode } from "../components/StatusCode";

import { TokenCostTooltip, TokenCountTooltip, TruncatedText } from "./common";

import { CopyableChip } from "@/components/common";
import { TypeChip } from "@/components/common/span/TypeChip";
import { SpanMetadataResponse } from "@/lib/api-client/api-client";
import { formatDate, formatDuration } from "@/utils/formatters";

const columnHelper = createColumnHelper<SpanMetadataResponse>();

export const spanLevelColumns = [
  columnHelper.accessor("span_kind", {
    header: "Span Kind",
    cell: ({ getValue }) => <TypeChip type={(getValue() as OpenInferenceSpanKind) ?? OpenInferenceSpanKind.AGENT} />,
    size: 80,
  }),
  columnHelper.accessor("status_code", {
    header: "Status",
    cell: ({ getValue }) => {
      const statusCode = getValue();
      return <StatusCode statusCode={isValidStatusCode(statusCode) ? statusCode : "Unset"} />;
    },
    size: 20,
  }),
  columnHelper.accessor("span_name", {
    header: "Span Name",
    cell: ({ getValue }) => getValue(),
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

  columnHelper.accessor("start_time", {
    header: "Start Time",
    cell: ({ getValue }) => formatDate(getValue()),
  }),
  columnHelper.accessor("duration_ms", {
    header: "Latency",
    cell: ({ getValue }) => formatDuration(getValue()),
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
