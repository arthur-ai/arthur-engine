import { OpenInferenceSpanKind, SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import dayjs from "dayjs";

import { SPAN_TYPE_ICONS } from "../constants";

import { NestedSpanWithMetricsResponse } from "@/lib/api";

export function getSpanInput(span?: NestedSpanWithMetricsResponse): string | null {
  const value = getNestedValue(span?.raw_data.attributes, SemanticConventions.INPUT_VALUE);
  return coerceToString(value);
}

export function getSpanOutput(span?: NestedSpanWithMetricsResponse): string | null {
  const value = getNestedValue(span?.raw_data.attributes, SemanticConventions.OUTPUT_VALUE);
  return coerceToString(value);
}

export function getSpanInputMimeType(span?: NestedSpanWithMetricsResponse) {
  return getNestedValue<"text/plain" | "application/json">(span?.raw_data.attributes, SemanticConventions.INPUT_MIME_TYPE) || null;
}

export function getSpanDuration(span?: NestedSpanWithMetricsResponse) {
  return span?.start_time && span?.end_time ? dayjs(span.end_time).diff(dayjs(span.start_time), "ms") : null;
}

export function flattenSpans(rootSpans: NestedSpanWithMetricsResponse[]): NestedSpanWithMetricsResponse[] {
  const result: NestedSpanWithMetricsResponse[] = [];

  function flattenRecursive(spans: NestedSpanWithMetricsResponse[]) {
    for (const span of spans) {
      result.push(span);
      if (span.children && span.children.length > 0) {
        flattenRecursive(span.children);
      }
    }
  }

  flattenRecursive(rootSpans);
  return result;
}

export function getSpanModel(span?: NestedSpanWithMetricsResponse): string | null {
  const value = getNestedValue(span?.raw_data.attributes, SemanticConventions.LLM_MODEL_NAME);
  return coerceToString(value);
}

export function getSpanType(span?: NestedSpanWithMetricsResponse) {
  return getNestedValue<OpenInferenceSpanKind>(span?.raw_data.attributes, SemanticConventions.OPENINFERENCE_SPAN_KIND);
}

export function getSpanIcon(span?: NestedSpanWithMetricsResponse) {
  const type = getSpanType(span) ?? OpenInferenceSpanKind.AGENT;

  const icon = SPAN_TYPE_ICONS[type] ?? SPAN_TYPE_ICONS[OpenInferenceSpanKind.AGENT];

  return icon;
}

export function isSpanOfType(span: NestedSpanWithMetricsResponse, type: OpenInferenceSpanKind) {
  return getSpanType(span) === type;
}

function coerceToString(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value || null;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function getNestedValue<Return>(obj: unknown, path: string): Return | undefined {
  if (typeof obj !== "object" || obj === null) return undefined;

  const keys = path.split(".");
  let current = obj;

  for (const key of keys) {
    if (current == null) return undefined;

    // handle numeric keys for arrays
    const index = Number(key);
    if (!Number.isNaN(index) && Array.isArray(current)) {
      current = current[index];
    } else if (typeof current === "object" && key in current) {
      current = current[key as keyof typeof current];
    } else {
      return undefined;
    }
  }

  return current as Return;
}
