import { PromptType } from "../types";

import { convertToolChoiceForBackend, filterNullParams } from ".";

import { CompletionRequest, ModelProvider, OpenAIMessageItem } from "@/lib/api-client/api-client";

const toCompletionRequest = (prompt: PromptType, keywords: Map<string, string>): CompletionRequest => {
  // Convert keywords Map to variables array for backend templating, filtering out empty values
  const variables = Array.from(keywords.entries())
    .filter(([name, value]) => value.trim() !== "") // Filter out empty or whitespace-only values
    .map(([name, value]) => ({
      name,
      value,
    }));

  // Keep messages as-is with template variables - backend will handle replacement
  const messages = prompt.messages.map((msg) => {
    // Transform tool_calls from OpenInference format to OpenAI format
    // OpenInference stores: { tool_call: { id, function } }
    // OpenAI expects: { id, type: "function", function }
    let processedToolCalls = null;
    if (msg.tool_calls && Array.isArray(msg.tool_calls)) {
      processedToolCalls = msg.tool_calls.map((tc: any) => ({
        id: tc.tool_call.id,
        type: "function",
        function: {
          name: tc.tool_call.function.name,
          arguments: tc.tool_call.function.arguments || "",
        },
      }));
    }

    return {
      role: msg.role,
      content: msg.content,
      name: msg.name || null,
      tool_call_id: msg.tool_call_id || null,
      tool_calls: processedToolCalls,
    };
  });

  return {
    model_name: prompt.modelName,
    model_provider: prompt.modelProvider as ModelProvider,
    messages,
    tools:
      prompt.tools.length > 0
        ? prompt.tools.map((tool) => ({
            function: {
              name: tool.function.name,
              description: tool.function.description,
              parameters: tool.function.parameters,
            },
            strict: tool.strict,
            type: tool.type,
          }))
        : undefined,
    completion_request: {
      stream: prompt.modelParameters.stream ?? false,
      variables: variables.length > 0 ? variables : undefined,
      strict: true, // Enforce strict validation - error if required variables are missing
    },
    config: filterNullParams({
      tool_choice: convertToolChoiceForBackend(prompt.toolChoice, prompt.tools),
      response_format: prompt.responseFormat ? JSON.parse(prompt.responseFormat) : null,
      temperature: prompt.modelParameters.temperature,
      // top_p: prompt.modelParameters.top_p,
      max_tokens: prompt.modelParameters.max_tokens,
      max_completion_tokens: prompt.modelParameters.max_completion_tokens,
      // frequency_penalty: prompt.modelParameters.frequency_penalty,
      // presence_penalty: prompt.modelParameters.presence_penalty,
      // stop: prompt.modelParameters.stop,
      seed: prompt.modelParameters.seed,
      // reasoning_effort: prompt.modelParameters.reasoning_effort,
      timeout: prompt.modelParameters.timeout,
      stream_options: prompt.modelParameters.stream_options,
      logprobs: prompt.modelParameters.logprobs,
      top_logprobs: prompt.modelParameters.top_logprobs,
      logit_bias: prompt.modelParameters.logit_bias,
      thinking: prompt.modelParameters.thinking,
    }),
  };
};

export default toCompletionRequest;
