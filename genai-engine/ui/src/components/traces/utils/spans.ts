import { getNestedValue } from "@arthur/shared-components";

import { NestedSpanWithMetricsResponse, StatusCodeEnum } from "@/lib/api";

export {
  getNestedValue,
  getSpanInput,
  getSpanOutput,
  getSpanInputMimeType,
  getSpanDuration,
  flattenSpans,
  getSpanModel,
  getSpanType,
  getSpanIcon,
  isSpanOfType,
} from "@arthur/shared-components";

export type SpanErrorInfo = {
  code: string;
  message: string;
  type?: string;
  stacktrace?: string;
};

type SpanStatus = { code?: unknown; message?: unknown };
type SpanEvent = { name?: unknown; attributes?: Record<string, unknown> };

const OTEL_KEYS = {
  status: "status",
  events: "events",
  exceptionEventName: "exception",
  exceptionMessage: "exception.message",
  exceptionType: "exception.type",
  exceptionStacktrace: "exception.stacktrace",
  defaultStatusCode: "STATUS_CODE_ERROR",
} as const;

const getStringAttr = (attrs: Record<string, unknown>, key: string): string | undefined => {
  const value = attrs[key];
  return typeof value === "string" ? value : undefined;
};

/**
 * Extracts a parsed error from a span when its status indicates an error.
 *
 * Primary source: the OpenTelemetry span status (`status.message` paired with
 * `status.code`). Falls back to the first OTel `exception` event's attributes
 * (`exception.message`, `exception.type`, `exception.stacktrace`) when the
 * status carries no message.
 *
 * Returns `null` when the span is not an error, or no extractable message is
 * present anywhere on the span.
 */
export function getSpanErrorInfo(span: NestedSpanWithMetricsResponse): SpanErrorInfo | null {
  if ((span.status_code as StatusCodeEnum) !== "Error") return null;

  const status = getNestedValue<SpanStatus>(span.raw_data, OTEL_KEYS.status);
  const statusMessage = typeof status?.message === "string" ? status.message : undefined;
  const statusCode = typeof status?.code === "string" ? status.code : OTEL_KEYS.defaultStatusCode;

  const events = getNestedValue<SpanEvent[]>(span.raw_data, OTEL_KEYS.events);
  const exceptionEvent = Array.isArray(events) ? events.find((e) => e.name === OTEL_KEYS.exceptionEventName) : undefined;
  const excAttrs = exceptionEvent?.attributes ?? {};
  const excMessage = getStringAttr(excAttrs, OTEL_KEYS.exceptionMessage);
  const excType = getStringAttr(excAttrs, OTEL_KEYS.exceptionType);
  const excStack = getStringAttr(excAttrs, OTEL_KEYS.exceptionStacktrace);

  const message = statusMessage ?? excMessage;
  if (!message) return null;

  return { code: statusCode, message, type: excType, stacktrace: excStack };
}

/**
 * Like getNestedValue but supports '*' as a wildcard segment.
 * When '*' is encountered on an array, iterates all items.
 * When '*' is encountered on an object, iterates all values.
 * Returns a flat array of all matched leaf values, or undefined if none found.
 */
export function getNestedValueWildcard<Return>(obj: unknown, path: string): Return[] | undefined {
  if (!path.includes("*")) {
    const result = getNestedValue<Return>(obj, path);
    return result !== undefined ? [result] : undefined;
  }

  if (typeof obj !== "object" || obj === null) return undefined;

  const keys = path.split(".");
  const results = collectWildcard(obj, keys, 0);
  return results.length > 0 ? (results as Return[]) : undefined;
}

function collectWildcard(current: unknown, keys: string[], index: number): unknown[] {
  if (index === keys.length) {
    return current != null ? [current] : [];
  }

  const key = keys[index];

  if (key === "*") {
    let items: unknown[];
    if (Array.isArray(current)) {
      items = current;
    } else if (typeof current === "object" && current !== null) {
      items = Object.values(current);
    } else {
      return [];
    }

    const results: unknown[] = [];
    for (const item of items) {
      results.push(...collectWildcard(item, keys, index + 1));
    }
    return results;
  }

  if (current == null) return [];

  const numIndex = Number(key);
  if (!Number.isNaN(numIndex) && Array.isArray(current)) {
    return collectWildcard(current[numIndex], keys, index + 1);
  }

  if (typeof current === "object" && key in current) {
    return collectWildcard((current as Record<string, unknown>)[key], keys, index + 1);
  }

  return [];
}
