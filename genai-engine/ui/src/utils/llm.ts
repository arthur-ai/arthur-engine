import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { z } from "zod";

import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { LLMOutputMessage, Message } from "@/schemas/llm";

const Messages = z.array(Message);

export function getMessages(span: NestedSpanWithMetricsResponse) {
  try {
    const messages = span.context?.map((message) => ({
      ...message,
      content: tryParseContent(message.content),
    }));

    return Messages.parse(messages);
  } catch {
    return [];
  }
}

const OutputMessages = z.array(LLMOutputMessage);

export function getOutputMessages(span: NestedSpanWithMetricsResponse) {
  const messages = span.response ? [tryParseContent(span.response)].flat() : [];
  try {
    return OutputMessages.parse(messages);
  } catch {
    return [];
  }
}

export function getInputTokens(span: NestedSpanWithMetricsResponse) {
  return (
    Number(
      span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_PROMPT]
    ) || 0
  );
}

export function getOutputTokens(span: NestedSpanWithMetricsResponse) {
  return (
    Number(
      span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_COMPLETION]
    ) || 0
  );
}

export function getTotalTokens(span: NestedSpanWithMetricsResponse) {
  return (
    Number(
      span.raw_data.attributes[SemanticConventions.LLM_TOKEN_COUNT_TOTAL]
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

function tryParseContent(content: string) {
  if (!content) return [];

  try {
    return JSON.parse(content);
  } catch {
    return [
      {
        type: "text",
        text: content,
      },
    ];
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function tryFormatJson(content: any) {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return JSON.stringify(content, null, 2);
  }
}
