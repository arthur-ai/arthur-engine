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

