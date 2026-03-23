import Tooltip from "@mui/material/Tooltip";
import { createMRTColumnHelper } from "material-react-table";

import { CopyableChip } from "../../common";
import { AnnotationCell } from "../components/AnnotationCell";
import { DurationCellWithBucket } from "../components/DurationCell";
import { TraceContentCell } from "../components/TraceContentCell";

import { TokenCostTooltip, TokenCountTooltip } from "./common";

import { TraceMetadataResponse } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { formatDate } from "@/utils/formatters";

const columnHelper = createMRTColumnHelper<TraceMetadataResponse>();

export const columns = [
  columnHelper.accessor("trace_id", {
    header: "Trace ID",
    size: 200,
    Cell: ({ cell }) => {
      const label = cell.getValue();
      return (
        <Tooltip title={label}>
          <span className="w-full">
            <CopyableChip
              label={label}
              sx={{ fontFamily: "monospace" }}
              onCopy={(value) =>
                track(EVENT_NAMES.TRACING_ID_COPIED, {
                  level: "trace",
                  id_type: "trace",
                  id_value: value,
                  source: "table",
                })
              }
            />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("annotations", {
    header: "Annotations",
    Cell: ({ cell, row }) => {
      const annotations = cell.getValue();

      if (!annotations) return;

      return <AnnotationCell annotations={annotations} traceId={row.original.trace_id ?? ""} />;
    },
  }),
  columnHelper.accessor("input_content", {
    header: "Input Content",
    Cell: ({ cell, row }) => (
      <span className="w-full">
        <TraceContentCell value={cell.getValue()} title="Trace Input Content" traceId={row.original.trace_id ?? undefined} />
      </span>
    ),
    size: 200,
  }),
  columnHelper.accessor("output_content", {
    header: "Output Content",
    Cell: ({ cell, row }) => (
      <span className="w-full">
        <TraceContentCell value={cell.getValue()} title="Trace Output Content" traceId={row.original.trace_id ?? undefined} />
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
  columnHelper.accessor("span_count", {
    header: "Span Count",
    Cell: ({ cell }) => `${cell.getValue()} spans`,
  }),
  columnHelper.accessor("start_time", {
    header: "Timestamp",
    Cell: ({ cell }) => formatDate(cell.getValue()),
    sortingFn: "datetime",
  }),
  columnHelper.accessor("duration_ms", {
    header: "Latency",
    Cell: ({ cell }) => <DurationCellWithBucket duration={cell.getValue()} />,
  }),
  columnHelper.accessor("session_id", {
    header: "Session ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();

      if (!label) return "-";

      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip
              label={label}
              sx={{ fontFamily: "monospace" }}
              onCopy={(value) =>
                track(EVENT_NAMES.TRACING_ID_COPIED, {
                  level: "trace",
                  id_type: "session",
                  id_value: value,
                  source: "table",
                })
              }
            />
          </span>
        </Tooltip>
      );
    },
  }),
  columnHelper.accessor("user_id", {
    header: "User ID",
    Cell: ({ cell }) => {
      const label = cell.getValue();

      if (!label) return "-";

      return (
        <Tooltip title={label}>
          <span>
            <CopyableChip
              label={label}
              sx={{ fontFamily: "monospace" }}
              onCopy={(value) =>
                track(EVENT_NAMES.TRACING_ID_COPIED, {
                  level: "trace",
                  id_type: "user",
                  id_value: value,
                  source: "table",
                })
              }
            />
          </span>
        </Tooltip>
      );
    },
  }),
];
