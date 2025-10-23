import { v4 as uuidv4 } from "uuid";

import { PromptType, promptClassificationEnum } from "./types";

import {
  AgenticPrompt,
  AgenticPromptBaseConfig,
  ToolChoiceEnum,
  ModelProvider,
  MessageRole,
  SpanWithMetricsResponse,
  JsonSchema,
  ToolCall,
} from "@/lib/api-client/api-client";

export const arrayUtils = {
  moveItem: <T>(array: T[], fromIndex: number, toIndex: number): T[] => {
    const newArray = [...array];
    const [item] = newArray.splice(fromIndex, 1);
    newArray.splice(toIndex, 0, item);
    return newArray;
  },

  duplicateAfter: <T>(array: T[], originalIndex: number, duplicate: T): T[] => [
    ...array.slice(0, originalIndex + 1),
    duplicate,
    ...array.slice(originalIndex + 1),
  ],
};

export const generateId = (type: "msg" | "tool") => {
  return type + "-" + uuidv4();
};

export const toBackendPrompt = (prompt: PromptType): AgenticPrompt => ({
  name: prompt.name,
  model_name: prompt.modelName,
  model_provider: prompt.provider as ModelProvider,
  messages: prompt.messages.map((msg) => ({
    role: msg.role,
    content: msg.content,
    tool_call_id: null,
    tool_calls: null,
  })),
  tools: prompt.tools.map((tool) => ({
    function: {
      name: tool.function.name,
      description: tool.function.description,
      parameters: tool.function.parameters,
    },
    strict: tool.strict,
    type: tool.type,
  })),
  tool_choice: prompt.toolChoice,
  temperature: prompt.modelParameters.temperature,
  top_p: prompt.modelParameters.top_p,
  timeout: prompt.modelParameters.timeout,
  stream_options: prompt.modelParameters.stream_options,
  max_tokens: prompt.modelParameters.max_tokens,
  max_completion_tokens: prompt.modelParameters.max_completion_tokens,
  frequency_penalty: prompt.modelParameters.frequency_penalty,
  presence_penalty: prompt.modelParameters.presence_penalty,
  stop: prompt.modelParameters.stop,
  seed: prompt.modelParameters.seed,
  reasoning_effort: prompt.modelParameters.reasoning_effort,
  logprobs: prompt.modelParameters.logprobs,
  top_logprobs: prompt.modelParameters.top_logprobs,
  logit_bias: prompt.modelParameters.logit_bias,
  thinking: prompt.modelParameters.thinking,
  response_format: prompt.responseFormat
    ? JSON.parse(prompt.responseFormat)
    : null,
});

export const toBackendPromptBaseConfig = (
  prompt: PromptType
): AgenticPromptBaseConfig => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { name, ...rest } = toBackendPrompt(prompt);
  return rest;
};

export const toFrontendPrompt = (backendPrompt: AgenticPrompt): PromptType => ({
  id: `${backendPrompt.name}-${new Date(
    backendPrompt.created_at ?? Date.now()
  ).getTime()}`,
  classification: "default",
  name: backendPrompt.name,
  created_at: backendPrompt.created_at || undefined,
  modelName: backendPrompt.model_name,
  provider: backendPrompt.model_provider,
  messages: backendPrompt.messages.map((msg) => ({
    id: `msg-${uuidv4()}`,
    role: msg.role,
    content: msg.content,
    disabled: false,
  })),
  tools: (backendPrompt.tools || []).map((tool) => ({
    id: generateId("tool"),
    function: {
      name: tool.function.name,
      description: tool.function.description,
      parameters: tool.function.parameters,
    },
    strict: tool.strict,
    type: tool.type,
  })),
  toolChoice: (backendPrompt.tool_choice as ToolChoiceEnum) || "auto",
  modelParameters: {
    temperature: backendPrompt.temperature ?? 1,
    top_p: backendPrompt.top_p ?? 1,
    timeout: backendPrompt.timeout,
    stream_options: backendPrompt.stream_options,
    max_tokens: backendPrompt.max_tokens,
    max_completion_tokens: backendPrompt.max_completion_tokens,
    frequency_penalty: backendPrompt.frequency_penalty ?? 0,
    presence_penalty: backendPrompt.presence_penalty ?? 0,
    stop: backendPrompt.stop,
    seed: backendPrompt.seed,
    reasoning_effort: backendPrompt.reasoning_effort,
    logprobs: backendPrompt.logprobs,
    top_logprobs: backendPrompt.top_logprobs,
    logit_bias: backendPrompt.logit_bias,
    thinking: backendPrompt.thinking,
  },
  outputField: "",
  responseFormat: backendPrompt.response_format
    ? JSON.stringify(backendPrompt.response_format)
    : undefined,
});

/**
 * Converts a span with metrics to a prompt format
 * Supports both OpenInference/OpenTelemetry and LiteLLM formats
 * @param spanData - The span data to convert
 * @param defaultModel - Default model name to use if not found in span
 * @param defaultProvider - Default provider to use if not found in span
 * @returns A prompt object created from the span data
 */
export const spanToPrompt = (
  spanData: SpanWithMetricsResponse,
  defaultModel: string = "gpt-4",
  defaultProvider: string = "openai"
): PromptType => {
  // Extract model information from raw_data attributes (supports both formats)
  const extractModelInfo = (rawData: Record<string, unknown>) => {
    const attributes = (rawData.attributes as Record<string, unknown>) || {};
    const metadataStr = attributes.metadata as string;
    const metadata = metadataStr ? JSON.parse(metadataStr) : {};

    // Try LiteLLM format first, then fall back to OpenInference format
    const modelName =
      (attributes["litellm.model"] as string) ||
      (attributes["llm.model_name"] as string) ||
      metadata.ls_model_name ||
      defaultModel;

    const provider =
      (attributes["litellm.provider"] as string) ||
      metadata.ls_provider ||
      defaultProvider;

    return { modelName, provider };
  };

  // Extract model parameters from LiteLLM attributes
  const extractModelParameters = (rawData: Record<string, unknown>) => {
    const attributes = (rawData.attributes as Record<string, unknown>) || {};

    return {
      temperature: (attributes["litellm.temperature"] as number) || 0.7,
      top_p: 1, // Default value, LiteLLM doesn't typically expose this
      max_tokens: (attributes["litellm.max_tokens"] as number) || 1000,
    };
  };

  // Convert context messages to prompt messages
  const convertContextToMessages = (
    context: Record<string, unknown>[] | null | undefined
  ) => {
    if (!context || !Array.isArray(context)) {
      return [];
    }

    return context.map((msg: Record<string, unknown>) => ({
      id: generateId("msg"),
      role: (msg.role as MessageRole) || "user",
      content: (msg.content as string) || "",
      disabled: false,
      tool_calls: (msg.tool_calls as ToolCall[]) || null,
      tool_call_id: (msg.tool_call_id as string) || null,
    }));
  };

  // Extract tools from context messages and LiteLLM attributes
  const extractTools = (
    context: Record<string, unknown>[] | null | undefined,
    rawData: Record<string, unknown>
  ) => {
    const tools: Array<{
      id: string;
      function: {
        name: string;
        description: string;
        parameters: JsonSchema;
      };
      strict: boolean;
      type: string;
    }> = [];
    const toolNames = new Set<string>();

    // First, try to extract tools from LiteLLM attributes
    const attributes = (rawData.attributes as Record<string, unknown>) || {};
    const litellmToolsStr = attributes["litellm.tools"] as string;

    if (litellmToolsStr) {
      try {
        const litellmTools = JSON.parse(litellmToolsStr) as Array<{
          type: string;
          function: {
            name: string;
            description: string;
            parameters: JsonSchema;
          };
        }>;

        litellmTools.forEach((tool) => {
          if (
            tool.type === "function" &&
            tool.function &&
            !toolNames.has(tool.function.name)
          ) {
            toolNames.add(tool.function.name);
            tools.push({
              id: generateId("tool"),
              function: {
                name: tool.function.name,
                description:
                  tool.function.description || `Tool: ${tool.function.name}`,
                parameters:
                  tool.function.parameters ||
                  ({
                    type: "object",
                    properties: {},
                    required: [],
                  } as JsonSchema),
              },
              strict: false,
              type: "function",
            });
          }
        });
      } catch (error) {
        console.warn("Failed to parse LiteLLM tools:", error);
      }
    }

    // Fallback: extract tools from context messages
    if (context && Array.isArray(context)) {
      context.forEach((msg: Record<string, unknown>) => {
        if (
          msg.role === "tool" &&
          msg.name &&
          !toolNames.has(msg.name as string)
        ) {
          const toolName = msg.name as string;
          toolNames.add(toolName);
          tools.push({
            id: generateId("tool"),
            function: {
              name: toolName,
              description: `Tool: ${toolName}`,
              parameters: {
                type: "object",
                properties: {},
                required: [],
              } as JsonSchema,
            },
            strict: false,
            type: "function",
          });
        }
      });
    }

    return tools;
  };

  const { modelName, provider } = extractModelInfo(spanData.raw_data);
  const modelParameters = extractModelParameters(spanData.raw_data);
  const messages = convertContextToMessages(spanData.context);
  const tools = extractTools(spanData.context, spanData.raw_data);

  // Create the prompt object
  const prompt: PromptType = {
    id: `span-prompt-${spanData.id}-${Date.now()}`,
    classification: promptClassificationEnum.DEFAULT,
    name: `Span: ${spanData.span_name || spanData.span_id || "Unknown"}`,
    created_at: spanData.created_at,
    modelName,
    provider,
    messages,
    modelParameters,
    outputField: spanData.response || "",
    responseFormat: undefined,
    tools,
    toolChoice: tools.length > 0 ? "auto" : undefined,
  };

  return prompt;
};
