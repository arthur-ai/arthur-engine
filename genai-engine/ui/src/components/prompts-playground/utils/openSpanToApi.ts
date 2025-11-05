import { extractContext, extractStatusCode } from ".";

import { SpanWithMetricsResponse } from "@/lib/api-client/api-client";

/**
 * Converts Unix nanoseconds timestamp to ISO date string
 */
const timestampNsToISO = (timestampNs: string | number): string => {
  const ns = typeof timestampNs === "string" ? BigInt(timestampNs) : BigInt(timestampNs);
  const ms = Number(ns / BigInt(1_000_000));
  return new Date(ms).toISOString();
};

/**
 * Raw OpenTelemetry/OpenInference span data format
 * This is the format received directly from OpenTelemetry collectors
 */
export interface RawOpenTelemetrySpan {
  kind?: string;
  name?: string;
  spanId: string;
  traceId: string;
  parentSpanId?: string;
  status?: unknown[] | { code?: string | number } | string;
  attributes: Record<string, unknown>;
  startTimeUnixNano: string | number;
  endTimeUnixNano: string | number;
  arthur_span_version?: string;
  events?: unknown[];
  links?: unknown[];
  resource?: Record<string, unknown>;
}

/**
 * Converts raw OpenTelemetry/OpenInference span data to SpanWithMetricsResponse format
 * @param rawSpan - Raw span data in OpenTelemetry/OpenInference format
 * @returns SpanWithMetricsResponse compatible with the API
 */
export const openSpanToApi = (rawSpan: RawOpenTelemetrySpan): SpanWithMetricsResponse => {
  const now = new Date().toISOString();
  const startTime = timestampNsToISO(rawSpan.startTimeUnixNano);
  const endTime = timestampNsToISO(rawSpan.endTimeUnixNano);
  const statusCode = extractStatusCode(rawSpan.status);
  const context = extractContext(rawSpan.attributes);

  // Convert spanId and traceId - they might be base64 encoded, keep as-is for now
  // The backend will handle conversion if needed
  const spanId = rawSpan.spanId;
  const traceId = rawSpan.traceId;

  // Extract span_kind from attributes or kind field
  const spanKind = (rawSpan.attributes["openinference.span.kind"] as string) || (rawSpan.attributes["span.kind"] as string) || rawSpan.kind || null;

  // Generate a unique ID for the span
  const id = `span-${spanId}-${Date.now()}`;

  return {
    id,
    trace_id: traceId,
    span_id: spanId,
    parent_span_id: rawSpan.parentSpanId || null,
    span_kind: spanKind,
    span_name: rawSpan.name || null,
    start_time: startTime,
    end_time: endTime,
    task_id: null,
    session_id: (rawSpan.attributes["session.id"] as string) || null,
    status_code: statusCode,
    raw_data: rawSpan as unknown as Record<string, unknown>,
    created_at: now,
    updated_at: now,
    context,
    system_prompt: null,
    user_query: null,
    response: null,
    metric_results: [],
  };
};

export default openSpanToApi;
