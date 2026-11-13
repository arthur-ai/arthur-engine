import type { TraceTransformVariableDefinition, TransformSpanSelector } from "@/lib/api-client/api-client";

// One transform variable as the form edits it: strings throughout, "" for unset.
export type VariableRow = {
  variable_name: string;
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

export const emptyVariableRow = (variable_name = ""): VariableRow => ({
  variable_name,
  span_name: "",
  span_kind: "",
  span_selector: "first",
  attribute_path: "",
  fallback: "",
});

export const variableToRow = (variable: TraceTransformVariableDefinition): VariableRow => ({
  variable_name: variable.variable_name,
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
  return {
    variable_name: row.variable_name,
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
