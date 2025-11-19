// Export the API client factory
export { getArthurApiClient } from "./client";

// Export prompt templating utilities
export {
  getTemplatedPrompt,
  type PromptVariable,
  type GetTemplatedPromptOptions,
  type TemplatedPromptResult,
} from "./prompt-templating";

// Re-export the Api class if needed
export { Api } from "./api-client";
