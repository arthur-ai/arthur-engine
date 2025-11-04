import { v4 as uuidv4 } from "uuid";

import { replaceKeywords } from "./mustacheExtractor";
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
  CompletionRequest,
  OpenAIMessageItem,
} from "@/lib/api-client/api-client";

/**
 * Raw OpenTelemetry/OpenInference span data format
 * This is the format received directly from OpenTelemetry collectors
 */
export interface RawOpenTelemetrySpan {
  kind?: string;
  name?: string;
  spanId: string;
  traceId: string;
  parentSpanId?: string;
  status?: unknown[] | { code?: string | number } | string;
  attributes: Record<string, unknown>;
  startTimeUnixNano: string | number;
  endTimeUnixNano: string | number;
  arthur_span_version?: string;
  events?: unknown[];
  links?: unknown[];
  resource?: Record<string, unknown>;
}

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
  model_provider: prompt.modelProvider as ModelProvider,
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
  response_format: prompt.responseFormat ? JSON.parse(prompt.responseFormat) : null,
});

export const toBackendPromptBaseConfig = (prompt: PromptType): AgenticPromptBaseConfig => {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { name, ...rest } = toBackendPrompt(prompt);
  return rest;
};

export const toFrontendPrompt = (backendPrompt: AgenticPrompt): PromptType => ({
  id: `${backendPrompt.name}-${new Date(backendPrompt.created_at ?? Date.now()).getTime()}`,
  classification: "default",
  name: backendPrompt.name,
  created_at: backendPrompt.created_at || undefined,
  modelName: backendPrompt.model_name,
  modelProvider: backendPrompt.model_provider,
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
  runResponse: null,
  responseFormat: backendPrompt.response_format ? JSON.stringify(backendPrompt.response_format) : undefined,
  running: false,
  version: backendPrompt.version || null,
});

/**
 * Converts Unix nanoseconds timestamp to ISO date string
 */
const timestampNsToISO = (timestampNs: string | number): string => {
  const ns = typeof timestampNs === "string" ? BigInt(timestampNs) : BigInt(timestampNs);
  const ms = Number(ns / BigInt(1_000_000));
  return new Date(ms).toISOString();
};

/**
 * Extracts status code from status field (can be array, object, or string)
 */
const extractStatusCode = (status: unknown[] | { code?: string | number } | string | undefined): string => {
  if (!status) {
    return "Unset";
  }
  if (typeof status === "string") {
    return status;
  }
  if (Array.isArray(status)) {
    if (status.length === 0) {
      return "Unset";
    }
    const first = status[0];
    if (typeof first === "object" && first !== null && "code" in first) {
      const code = first.code;
      if (typeof code === "string") return code;
      if (typeof code === "number") {
        // Map numeric codes: 1=Ok, 2=Error, 0/undefined=Unset
        if (code === 1) return "Ok";
        if (code === 2) return "Error";
        return "Unset";
      }
    }
    return "Unset";
  }
  if (typeof status === "object" && status !== null && "code" in status) {
    const code = status.code;
    if (typeof code === "string") return code;
    if (typeof code === "number") {
      if (code === 1) return "Ok";
      if (code === 2) return "Error";
      return "Unset";
    }
  }
  return "Unset";
};

/**
 * Extracts context from attributes if available (OpenInference format)
 */
const extractContext = (attributes: Record<string, unknown>): Record<string, unknown>[] | null => {
  // Check for OpenInference context in attributes
  const input = attributes.input as { value?: unknown } | undefined;
  if (input?.value && Array.isArray(input.value)) {
    return input.value as Record<string, unknown>[];
  }
  // Check for other context formats
  if (attributes.context && Array.isArray(attributes.context)) {
    return attributes.context as Record<string, unknown>[];
  }
  return null;
};

/**
 * Converts raw OpenTelemetry/OpenInference span data to SpanWithMetricsResponse format
 * @param rawSpan - Raw span data in OpenTelemetry/OpenInference format
 * @returns SpanWithMetricsResponse compatible with the API
 */
export const openSpanToApi = (rawSpan: RawOpenTelemetrySpan): SpanWithMetricsResponse => {
  const now = new Date().toISOString();
  const startTime = timestampNsToISO(rawSpan.startTimeUnixNano);
  const endTime = timestampNsToISO(rawSpan.endTimeUnixNano);
  const statusCode = extractStatusCode(rawSpan.status);
  const context = extractContext(rawSpan.attributes);

  // Convert spanId and traceId - they might be base64 encoded, keep as-is for now
  // The backend will handle conversion if needed
  const spanId = rawSpan.spanId;
  const traceId = rawSpan.traceId;

  // Extract span_kind from attributes or kind field
  const spanKind = (rawSpan.attributes["openinference.span.kind"] as string) || (rawSpan.attributes["span.kind"] as string) || rawSpan.kind || null;

  // Generate a unique ID for the span
  const id = `span-${spanId}-${Date.now()}`;

  return {
    id,
    trace_id: traceId,
    span_id: spanId,
    parent_span_id: rawSpan.parentSpanId || null,
    span_kind: spanKind,
    span_name: rawSpan.name || null,
    start_time: startTime,
    end_time: endTime,
    task_id: null,
    session_id: (rawSpan.attributes["session.id"] as string) || null,
    status_code: statusCode,
    raw_data: rawSpan as unknown as Record<string, unknown>,
    created_at: now,
    updated_at: now,
    context,
    system_prompt: null,
    user_query: null,
    response: null,
    metric_results: [],
  };
};

/**
 * Converts a SpanWithMetricsResponse (API format) to a frontend prompt format
 * Supports both OpenInference/OpenTelemetry and LiteLLM formats
 * @param spanData - The span data in API format to convert
 * @param defaultModel - Default model name to use if not found in span
 * @param defaultProvider - Default provider to use if not found in span
 * @returns A prompt object created from the span data
 */
export const apiToFrontendPrompt = (
  spanData: SpanWithMetricsResponse,
  defaultModel: string = "gpt-4",
  defaultProvider: string = "openai"
): PromptType => {
  // Extract model information from raw_data attributes (supports both formats)
  const extractModelInfo = (rawData: Record<string, unknown>) => {
    const attributes = (rawData.attributes as Record<string, unknown>) || {};

    // Handle metadata - can be either a JSON string or an object
    let metadata: Record<string, unknown> = {};
    if (attributes.metadata) {
      if (typeof attributes.metadata === "string") {
        try {
          metadata = JSON.parse(attributes.metadata);
        } catch {
          // If parsing fails, treat as empty object
          metadata = {};
        }
      } else if (typeof attributes.metadata === "object" && attributes.metadata !== null) {
        metadata = attributes.metadata as Record<string, unknown>;
      }
    }

    // Try LiteLLM format first, then fall back to OpenInference format
    const modelName =
      (attributes["litellm.model"] as string) || (attributes["llm.model_name"] as string) || (metadata.ls_model_name as string) || defaultModel;

    const modelProvider = ((attributes["litellm.provider"] as string) || (metadata.ls_provider as string) || defaultProvider) as ModelProvider | "";

    return { modelName, modelProvider };
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
  const convertContextToMessages = (context: Record<string, unknown>[] | null | undefined) => {
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
  const extractTools = (context: Record<string, unknown>[] | null | undefined, rawData: Record<string, unknown>) => {
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
          if (tool.type === "function" && tool.function && !toolNames.has(tool.function.name)) {
            toolNames.add(tool.function.name);
            tools.push({
              id: generateId("tool"),
              function: {
                name: tool.function.name,
                description: tool.function.description || `Tool: ${tool.function.name}`,
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
        if (msg.role === "tool" && msg.name && !toolNames.has(msg.name as string)) {
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

  const { modelName, modelProvider } = extractModelInfo(spanData.raw_data);
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
    modelProvider,
    messages,
    modelParameters,
    runResponse: null, // TODO
    responseFormat: undefined,
    tools,
    toolChoice: tools.length > 0 ? "auto" : undefined,
  };

  return prompt;
};

export const toCompletionRequest = (prompt: PromptType, keywords: Map<string, string>): CompletionRequest => {
  // Replace keywords in all message content
  const messages = prompt.messages.map((msg) => {
    // Handle content replacement: only replace if content is a string
    // The API accepts: string | OpenAIMessageItem[] | null | undefined
    let processedContent: string | OpenAIMessageItem[] | null | undefined = msg.content;
    if (typeof msg.content === "string") {
      processedContent = replaceKeywords(msg.content, keywords);
    }
    // If content is null/undefined or an array, keep it as is (API accepts these)

    return {
      role: msg.role,
      content: processedContent,
      name: msg.name || null,
      tool_call_id: msg.tool_call_id || null,
      tool_calls: msg.tool_calls || null,
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
    tool_choice: prompt.toolChoice,
    temperature: prompt.modelParameters.temperature,
    // top_p: prompt.modelParameters.top_p,
    max_tokens: prompt.modelParameters.max_tokens,
    max_completion_tokens: prompt.modelParameters.max_completion_tokens,
    // frequency_penalty: prompt.modelParameters.frequency_penalty,
    // presence_penalty: prompt.modelParameters.presence_penalty,
    stop: prompt.modelParameters.stop,
    seed: prompt.modelParameters.seed,
    // reasoning_effort: prompt.modelParameters.reasoning_effort,
    response_format: prompt.responseFormat ? JSON.parse(prompt.responseFormat) : null,
    timeout: prompt.modelParameters.timeout,
    stream_options: prompt.modelParameters.stream_options,
    logprobs: prompt.modelParameters.logprobs,
    top_logprobs: prompt.modelParameters.top_logprobs,
    logit_bias: prompt.modelParameters.logit_bias,
    thinking: prompt.modelParameters.thinking,
  };
};
