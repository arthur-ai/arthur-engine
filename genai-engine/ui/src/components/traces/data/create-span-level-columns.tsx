import { OpenInferenceSpanKind } from "@arizeai/openinference-semantic-conventions";
import { createMRTColumnHelper } from "material-react-table";

import type { ColumnDependencies } from "./column-factory-types";
import { createContentColumns, createDateColumn, createIdColumn, createTokenColumns } from "./column-utils";

import type { SpanMetadataResponse } from "@/lib/api-client/api-client";

const columnHelper = createMRTColumnHelper<SpanMetadataResponse>();

export const createSpanLevelColumns = (deps: ColumnDependencies) => {
  const { DurationCell, SpanStatusBadge, TypeChip, isValidStatusCode } = deps;

  return [
    columnHelper.accessor("span_kind", {
      header: "Span Kind",
      Cell: ({ cell }) => <TypeChip type={(cell.getValue() as OpenInferenceSpanKind) ?? OpenInferenceSpanKind.AGENT} />,
      size: 140,
    }),
    columnHelper.accessor("status_code", {
      header: "Status",
      Cell: ({ cell }) => {
        const statusCode = cell.getValue();
        const isValid = isValidStatusCode ? isValidStatusCode(statusCode) : statusCode === "Ok" || statusCode === "Error" || statusCode === "Unset";
        return <SpanStatusBadge status={isValid ? statusCode : "Unset"} />;
      },
      size: 120,
    }),
    columnHelper.accessor("span_name", {
      header: "Span Name",
      Cell: ({ cell }) => cell.getValue(),
    }),
    ...createContentColumns(columnHelper, deps, "Span", { includeSpanId: true }),
    ...createTokenColumns(columnHelper, deps),
    createIdColumn(columnHelper, "span_id", "Span ID", "span", "span", deps, {
      useFullWidth: true,
    }),
    createDateColumn(columnHelper, "start_time", "Start Time", deps),
    columnHelper.accessor("duration_ms", {
      header: "Latency",
      Cell: ({ cell }) => <DurationCell duration={cell.getValue()} />,
    }),
    createIdColumn(columnHelper, "trace_id", "Trace ID", "span", "trace", deps, {
      useFullWidth: true,
    }),
    createIdColumn(columnHelper, "session_id", "Session ID", "span", "session", deps, {
      emptyValue: null,
      useFullWidth: true,
    }),
    createIdColumn(columnHelper, "user_id", "User ID", "span", "user", deps, {
      emptyValue: null,
      useFullWidth: true,
    }),
  ];
};
