import {
  OpenInferenceSpanKind,
  SemanticConventions,
} from "@arizeai/openinference-semantic-conventions";
import dayjs from "dayjs";

import { SPAN_TYPE_ICONS } from "../constants";

import { NestedSpanWithMetricsResponse, TraceResponse } from "@/lib/api";

export function getSpanInput(span?: NestedSpanWithMetricsResponse) {
  return (
    getNestedValue<string>(
      span?.raw_data.attributes,
      SemanticConventions.INPUT_VALUE
    ) || null
  );
}

export function getSpanOutput(span?: NestedSpanWithMetricsResponse) {
  return (
    getNestedValue<string>(
      span?.raw_data.attributes,
      SemanticConventions.OUTPUT_VALUE
    ) || null
  );
}

export function getSpanInputMimeType(span?: NestedSpanWithMetricsResponse) {
  return (
    getNestedValue<"text/plain" | "application/json">(
      span?.raw_data.attributes,
      SemanticConventions.INPUT_MIME_TYPE
    ) || null
  );
}

export function getSpanDuration(span?: NestedSpanWithMetricsResponse) {
  return span?.start_time && span?.end_time
    ? dayjs(span.end_time).diff(dayjs(span.start_time), "ms")
    : null;
}

export function flattenSpans(
  rootSpans: NestedSpanWithMetricsResponse[]
): NestedSpanWithMetricsResponse[] {
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

export function getSpanModel(span?: NestedSpanWithMetricsResponse) {
  return (
    getNestedValue<string>(
      span?.raw_data.attributes,
      SemanticConventions.LLM_MODEL_NAME
    ) || null
  );
}

export function getSpanCost(span?: NestedSpanWithMetricsResponse) {
  return (
    Number(
      getNestedValue<number>(
        span?.raw_data.attributes,
        SemanticConventions.LLM_COST
      )
    ) || 0
  );
}

export function getSpanType(span?: NestedSpanWithMetricsResponse) {
  return getNestedValue<OpenInferenceSpanKind>(
    span?.raw_data.attributes,
    SemanticConventions.OPENINFERENCE_SPAN_KIND
  );
}

export function getSpanIcon(span?: NestedSpanWithMetricsResponse) {
  const type = getSpanType(span) ?? OpenInferenceSpanKind.AGENT;

  const icon = SPAN_TYPE_ICONS[type];

  return icon;
}

export function isSpanOfType(
  span: NestedSpanWithMetricsResponse,
  type: OpenInferenceSpanKind
) {
  return getSpanType(span) === type;
}

export function getNestedValue<Return extends any>(
  obj: unknown,
  path: string
): Return | undefined {
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
