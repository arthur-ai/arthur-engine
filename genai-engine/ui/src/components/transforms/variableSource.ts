import type { TraceTransformVariableDefinition, TransformVariableSource } from "@/lib/api-client/api-client";

// Mirrors MIN_MAX_CHARS and DEFAULT_MAX_CHARS in genai-engine/src/utils/trace_serializer.py
export const MIN_TRACE_MAX_CHARS = 2000;
export const DEFAULT_TRACE_MAX_CHARS = 48000;

export const VARIABLE_SOURCES: { value: TransformVariableSource; label: string; description: string }[] = [
  {
    value: "span",
    label: "A span",
    description: "Reads one attribute from the spans with this name. If several match, every one is read, in trace order.",
  },
  {
    value: "trace",
    label: "The whole trace",
    description: "Every span of the trace as text a judge can read, such as all attempts of a retried tool call.",
  },
];

export const isWholeTrace = (variable: Pick<TraceTransformVariableDefinition, "source">): boolean => variable.source === "trace";

/** What a preview says about where a variable's value came from. */
export const describeSpansRead = (
  variable: Pick<TraceTransformVariableDefinition, "source" | "span_name" | "attribute_path">,
  spanIds: string[]
): string => {
  if (isWholeTrace(variable)) {
    return `whole trace · ${spanIds.length} ${spanIds.length === 1 ? "span" : "spans"}`;
  }
  if (spanIds.length === 0) return "";
  if (spanIds.length === 1) return `${variable.span_name}.${variable.attribute_path}`;
  return `${variable.span_name} × ${spanIds.length}, in trace order`;
};

/** Errors for the whole-trace size budget, given as typed text ("" means the default). */
export const validateMaxChars = (value: string): string | null => {
  if (!value.trim()) return null;
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < MIN_TRACE_MAX_CHARS) {
    return `Size budget must be a whole number of at least ${MIN_TRACE_MAX_CHARS.toLocaleString()} characters`;
  }
  return null;
};
