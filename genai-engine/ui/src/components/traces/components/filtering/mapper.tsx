import { TIME_RANGES, type TimeRange } from "../../constants";

import { type Operator, Operators } from "./types";

import type { ContinuousEvalRunStatus } from "@/lib/api-client/api-client";

export type IncomingFilter = {
  name: string;
  operator: Operator;
  value: string | string[];
};

const OPERATOR_TO_KEY_PART = new Map<Operator, string>([
  [Operators.IN, "in"],
  [Operators.NOT_IN, "not_in"],
  [Operators.EQUALS, "eq"],
  [Operators.LESS_THAN, "lt"],
  [Operators.LESS_THAN_OR_EQUAL, "lte"],
  [Operators.GREATER_THAN, "gt"],
  [Operators.GREATER_THAN_OR_EQUAL, "gte"],
]);

export const mapFiltersToRequest = (filters: IncomingFilter[]) => {
  const request: Record<string, string | number | string[] | boolean> = {};

  filters.forEach((filter) => {
    let key = filter.name;

    // Handle array fields that should always be arrays
    if (key === "span_types" || key === "trace_ids" || key === "span_ids" || key === "session_ids" || key === "user_ids" || key === "status_code") {
      return (request[key] = [filter.value].flat());
    }

    if (key === "annotation_score") {
      return (request[key] = Number(filter.value));
    }

    // Special handling for span_name with CONTAINS operator
    if (key === "span_name" && filter.operator === Operators.CONTAINS) {
      return (request["span_name_contains"] = filter.value as string);
    }

    // Special handling for span_name with EQUALS operator (backend expects "span_name", not "span_name_eq")
    if (key === "span_name" && filter.operator === Operators.EQUALS) {
      return (request["span_name"] = filter.value as string);
    }

    if (key === "annotation_type" && filter.operator === Operators.EQUALS) {
      return (request["annotation_type"] = filter.value as "human" | "continuous_eval");
    }

    if (key === "continuous_eval_run_status" && filter.operator === Operators.EQUALS) {
      return (request["continuous_eval_run_status"] = filter.value as ContinuousEvalRunStatus);
    }

    if (key === "continuous_eval_name" && filter.operator === Operators.CONTAINS) {
      return (request["continuous_eval_name"] = filter.value as string);
    }

    // Special handling for continuous_eval_id with EQUALS operator (backend expects "continuous_eval_id", not "continuous_eval_id_eq")
    if (key === "continuous_eval_id" && filter.operator === Operators.EQUALS) {
      return (request["continuous_eval_id"] = filter.value as string);
    }

    // Special handling for trace_id with EQUALS operator (backend expects "trace_id", not "trace_id_eq")
    if (key === "trace_id" && filter.operator === Operators.EQUALS) {
      return (request["trace_id"] = filter.value as string);
    }

    // Special handling for id with IN operator (backend expects "id_in")
    if (key === "id" && filter.operator === Operators.IN) {
      return (request["id_in"] = filter.value as string[]);
    }

    // Handle boolean fields
    if (key === "include_experiment_traces" && filter.operator === Operators.EQUALS) {
      const value = Array.isArray(filter.value) ? filter.value[0] : filter.value;
      const boolValue = typeof value === "boolean" ? value : value === "true";
      return (request["include_experiment_traces"] = boolValue);
    }

    // Tool name: backend expects "tool_name", not "tool_name_eq"
    if (key === "tool_name" && filter.operator === Operators.EQUALS) {
      return (request["tool_name"] = filter.value as string);
    }

    // Custom timestamp filters: map to start_time/end_time ISO strings
    if (key === "start_time" && filter.operator === Operators.GREATER_THAN_OR_EQUAL) {
      return (request["start_time"] = filter.value as string);
    }
    if (key === "end_time" && filter.operator === Operators.LESS_THAN_OR_EQUAL) {
      return (request["end_time"] = filter.value as string);
    }

    const keyPart = OPERATOR_TO_KEY_PART.get(filter.operator);

    if (keyPart) {
      key += `_${keyPart}`;
    }

    request[key] = isNaN(Number(filter.value)) ? filter.value : Number(filter.value);
  });

  return request;
};

const ONE_MINUTE = 60 * 1000;
const ONE_HOUR = 60 * ONE_MINUTE;
const ONE_DAY = 24 * ONE_HOUR;

export const getStartDate = (timeRange: TimeRange) => {
  const now = new Date();
  switch (timeRange) {
    case TIME_RANGES["5 minutes"]:
      return new Date(now.getTime() - 5 * ONE_MINUTE);
    case TIME_RANGES["30 minutes"]:
      return new Date(now.getTime() - 30 * ONE_MINUTE);
    case TIME_RANGES["1 day"]:
      return new Date(now.getTime() - 24 * ONE_HOUR);
    case TIME_RANGES["1 week"]:
      return new Date(now.getTime() - 7 * ONE_DAY);
    case TIME_RANGES["1 month"]:
      return new Date(now.getTime() - 30 * ONE_DAY);
    case TIME_RANGES["3 months"]:
      return new Date(now.getTime() - 90 * ONE_DAY);
    case TIME_RANGES["1 year"]:
      return new Date(now.getTime() - 365 * ONE_DAY);
    case TIME_RANGES["all time"]:
      return new Date(0);
    default:
      // eslint-disable-next-line no-case-declarations
      const exhaustiveCheck: never = timeRange;
      throw new Error(`Unhandled time range: ${exhaustiveCheck}`);
  }
};
