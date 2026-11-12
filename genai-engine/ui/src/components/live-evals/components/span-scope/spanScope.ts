import z from "zod";

import type {
  ContinuousEvalResponse,
  ContinuousEvalRollupRule,
  ContinuousEvalScope,
  ContinuousEvalSpanFilter,
  TraceTransformVariableDefinition,
} from "@/lib/api-client/api-client";

// The form holds the span settings as strings; "" means unset.
export type SpanScopeValues = {
  scope: ContinuousEvalScope;
  spanName: string;
  spanKind: string;
  // No default: a span-scope eval must say how span verdicts decide the trace.
  rollupRule: ContinuousEvalRollupRule | "";
  maxSpans: string;
};

export const DEFAULT_MAX_SPANS_PER_TRACE = 20;
export const MAX_SPANS_PER_TRACE_LIMIT = 200;

export const ROLLUP_RULES: { value: ContinuousEvalRollupRule; label: string; help: string }[] = [
  {
    value: "final_attempt",
    label: "Final attempt decides",
    help: "Spans with the same name under the same parent are attempts; only the last judged one decides, so a call that failed and was retried successfully passes the trace.",
  },
  {
    value: "any_fail",
    label: "Any failing span fails the trace",
    help: "For checks every span must pass, such as leaking personal data. A retried call that failed once still fails the trace.",
  },
];

export const defaultSpanScope = (): SpanScopeValues => ({
  scope: "trace",
  spanName: "",
  spanKind: "",
  rollupRule: "",
  maxSpans: String(DEFAULT_MAX_SPANS_PER_TRACE),
});

export const spanScopeSchema = z
  .object({
    scope: z.enum(["trace", "span"]),
    spanName: z.string(),
    spanKind: z.string(),
    rollupRule: z.enum(["", "any_fail", "final_attempt"]),
    maxSpans: z.string(),
  })
  .superRefine((value, ctx) => {
    if (value.scope !== "span") return;
    if (!value.spanName.trim() && !value.spanKind.trim()) {
      ctx.addIssue({ code: "custom", path: ["spanName"], message: "Span name or span kind is required" });
    }
    if (!value.rollupRule) {
      ctx.addIssue({ code: "custom", path: ["rollupRule"], message: "Choose how span verdicts decide the trace" });
    }
    const max = Number(value.maxSpans);
    if (!Number.isInteger(max) || max < 1 || max > MAX_SPANS_PER_TRACE_LIMIT) {
      ctx.addIssue({ code: "custom", path: ["maxSpans"], message: `Between 1 and ${MAX_SPANS_PER_TRACE_LIMIT}` });
    }
  });

export const spanFilterFromValues = (values: SpanScopeValues): ContinuousEvalSpanFilter | null =>
  values.scope === "span"
    ? {
        span_name: values.spanName.trim() || null,
        span_kind: values.spanKind.trim() || null,
        conditions: [],
      }
    : null;

/** The request fields for the scope settings; trace scope clears the span ones. */
export const spanScopeToRequest = (values: SpanScopeValues) => ({
  scope: values.scope,
  span_filter: spanFilterFromValues(values),
  rollup_rule: values.scope === "span" && values.rollupRule ? values.rollupRule : null,
  max_spans_per_trace: values.scope === "span" ? Number(values.maxSpans) : DEFAULT_MAX_SPANS_PER_TRACE,
});

export const spanScopeFromEval = (
  data: Pick<ContinuousEvalResponse, "scope" | "span_filter" | "rollup_rule" | "max_spans_per_trace">
): SpanScopeValues => ({
  scope: data.scope ?? "trace",
  spanName: data.span_filter?.span_name ?? "",
  spanKind: data.span_filter?.span_kind ?? "",
  rollupRule: data.rollup_rule ?? "",
  maxSpans: String(data.max_spans_per_trace ?? DEFAULT_MAX_SPANS_PER_TRACE),
});

/** Span filter as the spend estimate takes it, or null for trace scope or a half-filled form. */
export const spanFilterJson = (values: SpanScopeValues): string | null => {
  const filter = spanFilterFromValues(values);
  if (!filter || (!filter.span_name && !filter.span_kind)) return null;
  return JSON.stringify(filter);
};

export const describeSpanScopeCost = (values: SpanScopeValues): string =>
  `Each matching span is its own judge call: up to ${values.maxSpans || DEFAULT_MAX_SPANS_PER_TRACE} calls per trace instead of one. ` +
  "A variable that reads the whole trace or every match ('all') is sent again with every span, so its tokens are paid once per span.";

/** The transform definition an eval runs: the pinned version, or the latest. */
export const effectiveTransformVariables = (
  versions: { id: string; definition: { variables?: TraceTransformVariableDefinition[] } }[],
  transformVersionId: string | null | undefined
): TraceTransformVariableDefinition[] | undefined =>
  (transformVersionId ? versions.find((version) => version.id === transformVersionId) : versions[0])?.definition.variables;

/** The warning for whole-trace variables in a span-scope eval, or null when there are none. */
export const describeWholeTraceInSpanScope = (names: string[], maxSpans: string): string | null => {
  if (names.length === 0) return null;
  const listed = names.join(", ");
  const verb = names.length === 1 ? "reads" : "read";
  return (
    `${listed} ${verb} the whole trace, so it is sent again with every judged span: ` +
    `up to ${maxSpans || DEFAULT_MAX_SPANS_PER_TRACE} copies of the trace per trace. ` +
    "Judge the whole trace once with a trace-scope eval, or read the judged span ('Judged span' in the transform) instead."
  );
};
