import { MessageType } from "../types";

import { OpenAIMessageInput } from "@/lib/api-client/api-client";

/**
 * Converts MessageType[] to OpenAIMessageInput[] by stripping frontend-specific fields
 * (id and disabled) that are not needed for API calls.
 *
 * @param messages - Array of MessageType messages from the frontend
 * @returns Array of OpenAIMessageInput messages ready for API calls
 */
export const convertMessagesToApiFormat = (messages: MessageType[]): OpenAIMessageInput[] => {
  return messages.map((msg) => {
    // Strip id and disabled fields, keep all other OpenAIMessageInput fields
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { id, disabled, ...apiMessage } = msg;
    return apiMessage;
  });
};

/**
 * Regex patterns to detect template variables
 * - Mustache/Jinja2 variables: {{ variable }}
 * - Jinja2 statements: {% statement %}
 */
const MUSTACHE_VARIABLE_PATTERN = /\{\{[^}]+\}\}/;
const JINJA_STATEMENT_PATTERN = /\{%[^%]+%\}/;

/**
 * Checks if a text string contains any template patterns (mustache or jinja).
 *
 * @param text - The text to check
 * @returns true if the text contains template patterns, false otherwise
 */
const hasTemplatePatterns = (text: string): boolean => {
  return MUSTACHE_VARIABLE_PATTERN.test(text) || JINJA_STATEMENT_PATTERN.test(text);
};

/**
 * Checks if messages contain any template patterns (mustache or jinja).
 * This is used to optimize API calls by skipping variable extraction when no templates are present.
 *
 * @param messages - Array of MessageType messages to check
 * @returns true if any message contains template patterns, false otherwise
 */
export const hasTemplateVariables = (messages: MessageType[]): boolean => {
  if (messages.length === 0) {
    return false;
  }

  for (const message of messages) {
    if (!message.content) {
      continue;
    }

    if (typeof message.content === "string") {
      if (hasTemplatePatterns(message.content)) {
        return true;
      }
    } else if (Array.isArray(message.content)) {
      // Check OpenAIMessageItem[] content
      for (const item of message.content) {
        if (item.text && typeof item.text === "string" && hasTemplatePatterns(item.text)) {
          return true;
        }
      }
    }
  }

  return false;
};
