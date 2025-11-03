import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { z } from "zod";

import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { Message } from "@/schemas/llm";
import { getNestedValue } from "@/components/traces/utils/spans";

const Messages = z.array(z.record(z.enum(["message"]), Message));

export function getMessages(span: NestedSpanWithMetricsResponse) {
  const messages = getNestedValue(
    span.raw_data.attributes,
    SemanticConventions.LLM_INPUT_MESSAGES
  );

  try {
    return Messages.parse(messages);
  } catch {
    return [];
  }
}

export function getOutputMessages(span: NestedSpanWithMetricsResponse) {
  const messages = getNestedValue(
    span.raw_data.attributes,
    SemanticConventions.LLM_OUTPUT_MESSAGES
  );

  try {
    return Messages.parse(messages);
  } catch {
    return [];
  }
}

export function getInputTokens(span: NestedSpanWithMetricsResponse) {
  return (
    Number(
      getNestedValue(
        span.raw_data.attributes,
        SemanticConventions.LLM_TOKEN_COUNT_PROMPT
      )
    ) || 0
  );
}

export function getOutputTokens(span: NestedSpanWithMetricsResponse) {
  return (
    Number(
      getNestedValue(
        span.raw_data.attributes,
        SemanticConventions.LLM_TOKEN_COUNT_COMPLETION
      )
    ) || 0
  );
}

export function getTotalTokens(span: NestedSpanWithMetricsResponse) {
  return (
    Number(
      getNestedValue(
        span.raw_data.attributes,
        SemanticConventions.LLM_TOKEN_COUNT_TOTAL
      )
    ) || 0
  );
}

export function getRoleAccentColor(role: Message["role"]) {
  switch (role) {
    case "user":
      return "grey.100";
    default:
      return "white";
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function tryFormatJson(content: any) {
  if (!content) return "";
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return JSON.stringify(content, null, 2);
  }
}
