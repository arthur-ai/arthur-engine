import { SemanticConventions } from "@arizeai/openinference-semantic-conventions";
import { z } from "zod";

import { NestedSpanWithMetricsResponse } from "@/lib/api";
import { LLMOutputMessage, Message } from "@/schemas/llm";

const Messages = z.array(Message);

export function getMessages(span: NestedSpanWithMetricsResponse) {
  try {
    return Messages.parse([
      ...getMessagesGenerator(span, SemanticConventions.LLM_INPUT_MESSAGES),
    ]);
  } catch {
    return [];
  }
}

const OutputMessages = z.array(LLMOutputMessage);

export function getOutputMessages(
  span: NestedSpanWithMetricsResponse
): LLMOutputMessage[] {
  try {
    const messages = [
      ...getMessagesGenerator(span, SemanticConventions.LLM_OUTPUT_MESSAGES),
    ];

    // Try to parse as Messages first
    let parsed;

    parsed = Messages.safeParse(messages);
    if (parsed.success) {
      console.log({ parsed: parsed.data });
      return parsed.data.flatMap((message) => {
        return message.content
          .map((entry) => {
            if (entry.type === "text") {
              return {
                text: entry.text,
                files: [],
                sources: [],
                reasoning: [],
                object: null,
              };
            }
          })
          .filter((entry) => entry !== undefined);
      });
    }

    parsed = OutputMessages.safeParse(
      messages.map((message) => message.content)
    );
    if (parsed.success) {
      return parsed.data;
    }

    return [];
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

export function* getMessagesGenerator<T extends string>(
  span: NestedSpanWithMetricsResponse,
  key: T
) {
  let index = 0;
  const raw = span.raw_data.attributes;

  while (true) {
    const currentKey = `${key}.${index}`;
    const keys = Object.keys(raw).filter((k) => k.startsWith(currentKey));

    if (keys.length === 0) {
      break;
    }

    const rawObject = Object.fromEntries(
      keys.map((k) => [k.substring(currentKey.length + 1), raw[k]])
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function tryFormatJson(content: any) {
  if (!content) return "";
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return JSON.stringify(content, null, 2);
  }
}

export function isLLMOutputMessage(message: any): message is LLMOutputMessage {
  return (
    "files" in message ||
    "text" in message ||
    "sources" in message ||
    "reasoning" in message ||
    "object" in message
  );
}
