import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { z } from "zod";

import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { Message } from "@/schemas/llm";

const Messages = z.array(Message);

export function getMessages(span: NestedSpanWithMetricsResponse) {
  try {
    return Messages.parse([...getMessagesGenerator(span)]);
  } catch {
    return [];
  }
}

export function getOutputMessages(span: NestedSpanWithMetricsResponse) {
  const rawMessages =
    span.raw_data.attributes[SemanticConventions.OUTPUT_VALUE];

  return rawMessages;
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

export function* getMessagesGenerator(span: NestedSpanWithMetricsResponse) {
  let index = 0;
  const raw = span.raw_data.attributes;

  while (true) {
    const key = `${SemanticConventions.LLM_INPUT_MESSAGES}.${index}`;
    const keys = Object.keys(raw).filter((k) => k.startsWith(key));

    if (keys.length === 0) {
      break;
    }

    const rawObject = Object.fromEntries(
      keys.map((k) => [k.substring(key.length + 1), raw[k]])
    );

    const content = tryParseContent(
      rawObject[SemanticConventions.MESSAGE_CONTENT]
    );

    yield {
      role: rawObject[SemanticConventions.MESSAGE_ROLE],
      content,
    };

    index++;
  }
}
