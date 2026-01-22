import { createMRTColumnHelper } from "material-react-table";

import type { ColumnDependencies } from "./column-factory-types";
import { createContentColumns, createCountColumn, createDateColumn, createIdColumn, createTokenColumns } from "./column-utils";

import type { TraceMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<TraceMetadataResponse>();

export const createTraceLevelColumns = (deps: ColumnDependencies) => {
  const { DurationCell, AnnotationCell } = deps;

  return [
    createIdColumn(columnHelper, "trace_id", "Trace ID", "trace", "trace", deps, {
      size: 200,
      useFullWidth: true,
    }),
    columnHelper.accessor("annotations", {
      header: "Annotations",
      Cell: ({ cell, row }) => {
        const annotations = cell.getValue();

        if (!annotations) return;

        return <AnnotationCell annotations={annotations} traceId={row.original.trace_id ?? ""} />;
      },
    }),
    ...createContentColumns(columnHelper, deps, "Trace"),
    ...createTokenColumns(columnHelper, deps),
    createCountColumn(columnHelper, "span_count", "Span Count", "spans"),
    createDateColumn(columnHelper, "start_time", "Timestamp", deps, {
      sortingFn: "datetime",
    }),
    columnHelper.accessor("duration_ms", {
      header: "Latency",
      Cell: ({ cell }) => <DurationCell duration={cell.getValue()} />,
    }),
    createIdColumn(columnHelper, "session_id", "Session ID", "trace", "session", deps),
    createIdColumn(columnHelper, "user_id", "User ID", "trace", "user", deps),
  ];
};
