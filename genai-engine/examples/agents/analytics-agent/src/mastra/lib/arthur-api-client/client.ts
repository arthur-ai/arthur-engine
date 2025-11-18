import { Api } from "./api-client";

/**
 * Creates and returns a configured Arthur API client instance
 * using environment variables for authentication
 */
export function getArthurApiClient(): Api {
  return new Api({
    baseURL: process.env.ARTHUR_BASE_URL,
    headers: {
      Authorization: `Bearer ${process.env.ARTHUR_API_KEY}`,
    },
  });
}

// Re-export prompt templating utilities
export { getTemplatedPrompt } from "./prompt-templating";
export type {
  PromptVariable,
  GetTemplatedPromptOptions,
  TemplatedPromptResult,
} from "./prompt-templating";
