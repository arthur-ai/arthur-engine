import { PromptType } from "../types";
import { SavedPromptConfig, UnsavedPromptConfig } from "@/lib/api-client/api-client";

/**
 * Converts a playground prompt to an experiment prompt config
 * Returns either a SavedPromptConfig or UnsavedPromptConfig based on whether the prompt is saved
 */
export const toExperimentPromptConfig = (
  prompt: PromptType
): ({ type: "saved" } & SavedPromptConfig) | ({ type: "unsaved" } & UnsavedPromptConfig) => {
  // If prompt has a name and version, it's a saved prompt
  if (prompt.name && prompt.version !== null && prompt.version !== undefined) {
    return {
      type: "saved",
      name: prompt.name,
      version: prompt.version,
    };
  }

  // Otherwise, it's an unsaved prompt - need to include full prompt details
  // Convert messages to the format expected by the backend
  const messages = prompt.messages
    .filter((msg) => !msg.disabled)
    .map((msg) => ({
      role: msg.role,
      content: msg.content,
      ...(msg.tool_calls ? { tool_calls: msg.tool_calls } : {}),
    }));

  // Convert tools to the format expected by the backend
  const tools = prompt.tools.length > 0
    ? prompt.tools.map((tool) => ({
        type: tool.type,
        function: {
          name: tool.function.name,
          description: tool.function.description,
          parameters: tool.function.parameters,
        },
        ...(tool.strict !== undefined ? { strict: tool.strict } : {}),
      }))
    : undefined;

  // Convert model parameters - only include non-null values
  const config: Record<string, any> = {};
  if (prompt.modelParameters.temperature !== null) config.temperature = prompt.modelParameters.temperature;
  if (prompt.modelParameters.top_p !== null) config.top_p = prompt.modelParameters.top_p;
  if (prompt.modelParameters.timeout !== null) config.timeout = prompt.modelParameters.timeout;
  if (prompt.modelParameters.stream !== null) config.stream = prompt.modelParameters.stream;
  if (prompt.modelParameters.stream_options !== null) config.stream_options = prompt.modelParameters.stream_options;
  if (prompt.modelParameters.max_tokens !== null) config.max_tokens = prompt.modelParameters.max_tokens;
  if (prompt.modelParameters.max_completion_tokens !== null) config.max_completion_tokens = prompt.modelParameters.max_completion_tokens;
  if (prompt.modelParameters.frequency_penalty !== null) config.frequency_penalty = prompt.modelParameters.frequency_penalty;
  if (prompt.modelParameters.presence_penalty !== null) config.presence_penalty = prompt.modelParameters.presence_penalty;
  if (prompt.modelParameters.stop !== null) config.stop = prompt.modelParameters.stop;
  if (prompt.modelParameters.seed !== null) config.seed = prompt.modelParameters.seed;
  if (prompt.modelParameters.reasoning_effort !== null) config.reasoning_effort = prompt.modelParameters.reasoning_effort;
  if (prompt.modelParameters.logprobs !== null) config.logprobs = prompt.modelParameters.logprobs;
  if (prompt.modelParameters.top_logprobs !== null) config.top_logprobs = prompt.modelParameters.top_logprobs;
  if (prompt.modelParameters.logit_bias !== null) config.logit_bias = prompt.modelParameters.logit_bias;
  if (prompt.modelParameters.thinking !== null) config.thinking = prompt.modelParameters.thinking;

  // Add tool_choice if defined
  if (prompt.toolChoice !== undefined) {
    config.tool_choice = prompt.toolChoice;
  }

  // Add response_format if defined
  if (prompt.responseFormat !== undefined) {
    config.response_format = prompt.responseFormat;
  }

  return {
    type: "unsaved",
    messages,
    model_name: prompt.modelName,
    model_provider: prompt.modelProvider,
    config: Object.keys(config).length > 0 ? config : undefined,
    tools,
    variables: undefined, // Let backend auto-detect variables
  };
};
