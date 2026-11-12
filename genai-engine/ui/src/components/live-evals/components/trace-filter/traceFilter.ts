import z from "zod";

import type { ContinuousEvalTraceFilterCondition, ContinuousEvalTraceFilterOperator } from "@/lib/api-client/api-client";

// The form holds each condition as strings; "" means "any span" for spanName and
// "no value" for value.
export type TraceFilterRow = {
  spanName: string;
  attributePath: string;
  operator: ContinuousEvalTraceFilterOperator;
  value: string;
};

export const TRACE_FILTER_OPERATORS: { value: ContinuousEvalTraceFilterOperator; label: string }[] = [
  { value: "equals", label: "equals" },
  { value: "not_equals", label: "does not equal" },
  { value: "contains", label: "contains" },
  { value: "exists", label: "exists" },
];

export const emptyTraceFilterRow = (): TraceFilterRow => ({ spanName: "", attributePath: "", operator: "equals", value: "" });

export const traceFilterRowSchema = z
  .object({
    spanName: z.string(),
    attributePath: z.string().trim().min(1, { error: "Attribute path is required" }),
    operator: z.enum(["equals", "not_equals", "contains", "exists"]),
    value: z.string(),
  })
  .refine((row) => row.operator === "exists" || row.value.trim() !== "", {
    error: "Value is required unless the operator is exists",
    path: ["value"],
  });

export const traceFilterSchema = z.array(traceFilterRowSchema);

// The rows that are filled in enough to send, e.g. for an estimate while editing.
export const completeTraceFilterRows = (rows: TraceFilterRow[]): TraceFilterRow[] =>
  rows.filter((row) => traceFilterRowSchema.safeParse(row).success);

export const rowsToTraceFilter = (rows: TraceFilterRow[]): ContinuousEvalTraceFilterCondition[] | null =>
  rows.length === 0
    ? null
    : rows.map((row) => ({
        span_name: row.spanName.trim() || null,
        attribute_path: row.attributePath.trim(),
        operator: row.operator,
        value: row.operator === "exists" ? null : row.value,
      }));

export const traceFilterToRows = (traceFilter: ContinuousEvalTraceFilterCondition[] | null | undefined): TraceFilterRow[] =>
  (traceFilter ?? []).map((condition) => ({
    spanName: condition.span_name ?? "",
    attributePath: condition.attribute_path,
    operator: condition.operator,
    value: condition.value ?? "",
  }));
