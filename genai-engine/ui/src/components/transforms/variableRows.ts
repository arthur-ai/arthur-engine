import type { TraceTransformVariableDefinition, TransformSpanSelector, TransformVariableSource } from "@/lib/api-client/api-client";

// One transform variable as the form edits it: strings throughout, "" for unset.
export type VariableRow = {
  variable_name: string;
  // "trace" makes the value the whole trace as text; the span fields are then unused.
  source: TransformVariableSource;
  max_chars: string;
  span_name: string;
  span_kind: string;
  span_selector: TransformSpanSelector;
  attribute_path: string;
  fallback: string;
};

export const SPAN_SELECTORS: { value: TransformSpanSelector; label: string; help: string }[] = [
  { value: "first", label: "First match", help: "The first matching span in tree order." },
  { value: "last", label: "Last match", help: "The last matching span in tree order, e.g. a retried tool call." },
  { value: "all", label: "All matches", help: "Every matching span, joined into one value headed by span ids." },
  {
    value: "current",
    label: "Judged span",
    help: "The span a span-scope continuous eval is judging. Finds no span anywhere else.",
  },
];

export const MIN_TRACE_MAX_CHARS = 2000;
export const DEFAULT_TRACE_MAX_CHARS = 48000;

export const emptyVariableRow = (variable_name = ""): VariableRow => ({
  variable_name,
  source: "span",
  max_chars: "",
  span_name: "",
  span_kind: "",
  span_selector: "first",
  attribute_path: "",
  fallback: "",
});

export const variableToRow = (variable: TraceTransformVariableDefinition): VariableRow => ({
  variable_name: variable.variable_name,
  source: variable.source ?? "span",
  max_chars: variable.max_chars != null ? String(variable.max_chars) : "",
  span_name: variable.span_name ?? "",
  span_kind: variable.span_kind ?? "",
  span_selector: variable.span_selector ?? "first",
  attribute_path: variable.attribute_path,
  fallback: variable.fallback !== undefined && variable.fallback !== null ? JSON.stringify(variable.fallback) : "",
});

export const rowToVariable = (row: VariableRow): TraceTransformVariableDefinition => {
  let fallback: string | undefined;
  if (row.fallback.trim()) {
    const parsed = JSON.parse(row.fallback);
    fallback = parsed !== null ? parsed : undefined;
  }
  if (row.source === "trace") {
    // attribute_path is required by the shared model; a trace variable ignores it.
    return {
      variable_name: row.variable_name,
      source: "trace",
      max_chars: row.max_chars.trim() ? Number(row.max_chars) : null,
      attribute_path: "",
      fallback,
    };
  }
  return {
    variable_name: row.variable_name,
    source: "span",
    span_name: row.span_name.trim() || null,
    span_kind: row.span_kind.trim() || null,
    span_selector: row.span_selector,
    attribute_path: row.attribute_path,
    fallback,
  };
};

/** Errors for one row, numbered for the form's error list. */
export const validateVariableRow = (row: VariableRow, index: number): string[] => {
  const errors: string[] = [];
  const label = `Variable ${index + 1}`;
  if (!row.variable_name.trim()) errors.push(`${label}: Variable name is required`);
  if (row.source === "trace") {
    const max = Number(row.max_chars);
    if (row.max_chars.trim() && (!Number.isInteger(max) || max < MIN_TRACE_MAX_CHARS)) {
      errors.push(`${label}: Size budget must be a whole number of at least ${MIN_TRACE_MAX_CHARS} characters`);
    }
    return errors;
  }
  if (!row.span_name.trim() && !row.span_kind.trim() && row.span_selector !== "current") {
    errors.push(`${label}: Span name or span kind is required`);
  }
  if (!row.attribute_path.trim()) errors.push(`${label}: Attribute path is required`);
  if (row.fallback) {
    try {
      JSON.parse(row.fallback);
    } catch {
      errors.push(`${label}: Fallback must be valid JSON`);
    }
  }
  return errors;
};

/** How a variable's spans read in lists: "lookup_order (TOOL), last match". */
export const describeVariableSpans = (variable: TraceTransformVariableDefinition): string => {
  if (variable.source === "trace") return `the whole trace, up to ${(variable.max_chars ?? DEFAULT_TRACE_MAX_CHARS).toLocaleString()} chars`;
  const selector = variable.span_selector ?? "first";
  const target =
    variable.span_name && variable.span_kind
      ? `${variable.span_name} (${variable.span_kind})`
      : (variable.span_name ?? (variable.span_kind ? `any ${variable.span_kind} span` : "the judged span"));
  if (selector === "first") return target;
  const selectorLabel = SPAN_SELECTORS.find((s) => s.value === selector)?.label.toLowerCase() ?? selector;
  if (selector === "current") return variable.span_name || variable.span_kind ? `${target}, the judged span` : target;
  return `${target}, ${selectorLabel}`;
};

/** Variables whose value is the whole trace: in a span-scope eval each one is sent again with every span run. */
export const wholeTraceVariableNames = (variables: TraceTransformVariableDefinition[] | undefined): string[] =>
  (variables ?? []).filter((variable) => variable.source === "trace").map((variable) => variable.variable_name);
