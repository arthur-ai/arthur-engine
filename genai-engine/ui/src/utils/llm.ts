import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { z } from "zod";

import { getNestedValue } from "@/components/traces/utils/spans";
import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { LLMToolsField, Message, Tool } from "@/schemas/llm";

const Messages = z.array(z.object({ message: Message }));

export function getMessages(span: NestedSpanWithMetricsResponse) {
  const messages = getNestedValue(span.raw_data.attributes, SemanticConventions.LLM_INPUT_MESSAGES);

  try {
    return Messages.parse(messages);
  } catch {
    return [];
  }
}

export function getOutputMessages(span: NestedSpanWithMetricsResponse) {
  const messages = getNestedValue(span.raw_data.attributes, SemanticConventions.LLM_OUTPUT_MESSAGES);

  try {
    return Messages.parse(messages);
  } catch {
    return [];
  }
}

export function getInputTokens(span: NestedSpanWithMetricsResponse) {
  return span.prompt_token_count ?? undefined;
}

export function getOutputTokens(span: NestedSpanWithMetricsResponse) {
  return span.completion_token_count ?? undefined;
}

export function getTotalTokens(span: NestedSpanWithMetricsResponse) {
  return span.total_token_count ?? undefined;
}

export function getTokens(span: NestedSpanWithMetricsResponse) {
  return {
    input: getInputTokens(span),
    output: getOutputTokens(span),
    total: getTotalTokens(span),
  };
}

export function getCost(span: NestedSpanWithMetricsResponse) {
  return {
    prompt: span.prompt_token_cost ?? undefined,
    completion: span.completion_token_cost ?? undefined,
    total: span.total_token_cost ?? undefined,
  };
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

export function getTools(span: NestedSpanWithMetricsResponse) {
  const raw = getNestedValue(span.raw_data.attributes, SemanticConventions.LLM_TOOLS) ?? [];
  try {
    const rawTools = LLMToolsField.parse(raw).map(({ tool }) => JSON.parse(tool.json_schema));

    return rawTools.map((tool) => Tool.parse(tool));
  } catch (error) {
    console.log(JSON.stringify(raw, null, 2));
    console.error(error);
    return [];
  }
}
