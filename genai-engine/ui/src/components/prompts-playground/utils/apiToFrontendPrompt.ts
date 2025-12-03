import { PromptType, promptClassificationEnum } from "../types";

import { generateId } from ".";

import { JsonSchema, MessageRole, ModelProvider, OpenAIMessageItem, SpanWithMetricsResponse, ToolCall } from "@/lib/api-client/api-client";

/**
 * Converts a SpanWithMetricsResponse (API format) to a frontend prompt format
 * Supports both OpenInference/OpenTelemetry and LiteLLM formats
 * @param spanData - The span data in API format to convert
 * @param defaultModel - Default model name to use if not found in span
 * @param defaultProvider - Default provider to use if not found in span
 * @returns A prompt object created from the span data
 */
const apiToFrontendPrompt = (spanData: SpanWithMetricsResponse, defaultModel: string = "gpt-4", defaultProvider: string = "openai"): PromptType => {
  // Normalize provider name (e.g., "openai.responses" -> "openai")
  const normalizeProvider = (provider: string): string => {
    if (!provider) return provider;
    // Remove .responses, .stream, etc. suffixes
    return provider.split(".")[0];
  };

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

    // Try to extract model name from nested llm object first
    const llm = attributes.llm as { model_name?: string; provider?: string } | undefined;
    const nestedModelName = llm?.model_name;
    const nestedProvider = llm?.provider;

    // Try LiteLLM format first, then nested llm, then fall back to OpenInference format
    const modelName =
      (attributes["litellm.model"] as string) ||
      nestedModelName ||
      (attributes["llm.model_name"] as string) ||
      (metadata.ls_model_name as string) ||
      defaultModel;

    const rawProvider = (attributes["litellm.provider"] as string) || nestedProvider || (metadata.ls_provider as string) || defaultProvider;

    const modelProvider = normalizeProvider(rawProvider) as ModelProvider | "";

    return { modelName, modelProvider };
  };

  // Extract model parameters from LiteLLM attributes and llm.invocation_parameters
  const extractModelParameters = (rawData: Record<string, unknown>) => {
    const attributes = (rawData.attributes as Record<string, unknown>) || {};

    // Try to extract from nested llm.invocation_parameters
    const llm = attributes.llm as { invocation_parameters?: { temperature?: number; max_tokens?: number; top_p?: number } } | undefined;
    const invocationParams = llm?.invocation_parameters;

    return {
      temperature: invocationParams?.temperature ?? (attributes["litellm.temperature"] as number) ?? 0.7,
      top_p: invocationParams?.top_p ?? 1, // Default value, LiteLLM doesn't typically expose this
      max_tokens: invocationParams?.max_tokens ?? (attributes["litellm.max_tokens"] as number) ?? 1000,
    };
  };

  // Normalize content from various formats (string, array, nested)
  const normalizeContent = (content: unknown): string | OpenAIMessageItem[] => {
    if (!content) return "";

    // If it's already a string, return it
    if (typeof content === "string") {
      return content;
    }

    // If it's an array (multimodal content), return as-is
    if (Array.isArray(content)) {
      return content as OpenAIMessageItem[];
    }

    // If it's an object, try to extract text or convert to string
    if (typeof content === "object" && content !== null) {
      const contentObj = content as Record<string, unknown>;
      // Check if it has a text property
      if ("text" in contentObj && typeof contentObj.text === "string") {
        return contentObj.text;
      }
      // Fallback: stringify the object
      return JSON.stringify(content);
    }

    return String(content);
  };

  // Convert context messages to prompt messages
  // Handles both formats: direct { role, content } and nested { message: { role, content } }
  const convertContextToMessages = (context: Record<string, unknown>[] | null | undefined) => {
    if (!context || !Array.isArray(context)) {
      return [];
    }

    return context.map((msg: Record<string, unknown>) => {
      // Handle nested message format: { message: { role, content } }
      let messageData = msg;
      if (msg.message && typeof msg.message === "object" && msg.message !== null) {
        messageData = msg.message as Record<string, unknown>;
      }

      const role = (messageData.role as MessageRole) || "user";
      const content = normalizeContent(messageData.content);

      return {
        id: generateId("msg"),
        role,
        content,
        disabled: false,
        tool_calls: (messageData.tool_calls as ToolCall[]) || null,
        tool_call_id: (messageData.tool_call_id as string) || null,
      };
    });
  };

  // Extract tools from messages and LiteLLM attributes
  const extractTools = (
    messages: Array<{
      id: string;
      role: MessageRole;
      content: string | OpenAIMessageItem[];
      disabled: boolean;
      tool_calls: ToolCall[] | null;
      tool_call_id: string | null;
    }>,
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

    // Fallback: extract tools from tool_calls in messages
    if (messages && Array.isArray(messages)) {
      messages.forEach((msg) => {
        if (msg.tool_calls && Array.isArray(msg.tool_calls)) {
          msg.tool_calls.forEach((toolCall) => {
            if (toolCall.function && !toolNames.has(toolCall.function.name)) {
              const toolName = toolCall.function.name;
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
      });
    }

    return tools;
  };

  // Extract input messages from llm.input_messages
  const extractInputMessages = (rawData: Record<string, unknown>) => {
    const attributes = (rawData.attributes as Record<string, unknown>) || {};
    const llm = attributes.llm as
      | {
          input_messages?: Array<{
            message?: {
              role?: string;
              content?: unknown;
              tool_calls?: ToolCall[];
              tool_call_id?: string;
            };
          }>;
        }
      | undefined;

    if (!llm?.input_messages || !Array.isArray(llm.input_messages)) {
      return [];
    }

    return llm.input_messages
      .map((inputMsg) => {
        const msg = inputMsg.message;
        if (!msg || typeof msg !== "object") {
          return null;
        }

        const role = (msg.role as MessageRole) || "user";
        const content = normalizeContent(msg.content);

        return {
          id: generateId("msg"),
          role,
          content,
          disabled: false,
          tool_calls: (msg.tool_calls as ToolCall[]) || null,
          tool_call_id: (msg.tool_call_id as string) || null,
        };
      })
      .filter((msg) => msg !== null) as Array<{
      id: string;
      role: MessageRole;
      content: string | OpenAIMessageItem[];
      disabled: boolean;
      tool_calls: ToolCall[] | null;
      tool_call_id: string | null;
    }>;
  };

  // Extract assistant messages from llm.output_messages
  const extractOutputMessages = (rawData: Record<string, unknown>) => {
    const attributes = (rawData.attributes as Record<string, unknown>) || {};
    const llm = attributes.llm as
      | {
          output_messages?: Array<{
            message?: {
              role?: string;
              content?: unknown;
              tool_calls?: ToolCall[];
              tool_call_id?: string;
            };
          }>;
        }
      | undefined;

    if (!llm?.output_messages || !Array.isArray(llm.output_messages)) {
      return [];
    }

    return llm.output_messages
      .map((outputMsg) => {
        const msg = outputMsg.message;
        if (!msg || typeof msg !== "object") {
          return null;
        }

        const role = (msg.role as MessageRole) || "assistant";
        const content = normalizeContent(msg.content);

        return {
          id: generateId("msg"),
          role,
          content,
          disabled: false,
          tool_calls: (msg.tool_calls as ToolCall[]) || null,
          tool_call_id: (msg.tool_call_id as string) || null,
        };
      })
      .filter((msg) => msg !== null) as Array<{
      id: string;
      role: MessageRole;
      content: string | OpenAIMessageItem[];
      disabled: boolean;
      tool_calls: ToolCall[] | null;
      tool_call_id: string | null;
    }>;
  };

  const { modelName, modelProvider } = extractModelInfo(spanData.raw_data);
  const modelParameters = extractModelParameters(spanData.raw_data);
  const inputMessages = extractInputMessages(spanData.raw_data);
  const outputMessages = extractOutputMessages(spanData.raw_data);

  // Filter out the final assistant response with tool_calls from input messages
  // because it will be in the output messages. Tool response messages that follow
  // should also be excluded if they're responding to the final assistant message.
  const filteredInputMessages = inputMessages.filter((msg, index) => {
    // If this is an assistant message with tool_calls, check if it's the last one
    if (msg.role === "assistant" && msg.tool_calls && msg.tool_calls.length > 0) {
      // Check if this assistant message is followed only by tool responses
      const remainingMessages = inputMessages.slice(index + 1);
      const allToolResponses = remainingMessages.every((m) => m.role === "tool");

      // If followed only by tool responses (or nothing), this is likely the final turn
      // that's being responded to, so exclude it and its tool responses
      if (allToolResponses) {
        return false;
      }
    }

    // If this is a tool message, check if it's responding to an excluded assistant message
    if (msg.role === "tool") {
      // Find the most recent assistant message with tool_calls before this
      for (let i = index - 1; i >= 0; i--) {
        const prevMsg = inputMessages[i];
        if (prevMsg.role === "assistant" && prevMsg.tool_calls && prevMsg.tool_calls.length > 0) {
          // Check if that assistant message will be excluded
          const remainingAfterAssistant = inputMessages.slice(i + 1);
          const allToolResponsesAfter = remainingAfterAssistant.every((m) => m.role === "tool");
          if (allToolResponsesAfter) {
            return false; // Exclude this tool message too
          }
          break;
        }
      }
    }

    return true;
  });

  // Create runResponse from the first output message
  const assistantMessage = outputMessages.length > 0 ? outputMessages[0] : null;
  const runResponse = assistantMessage
    ? {
        content: typeof assistantMessage.content === "string" ? assistantMessage.content : JSON.stringify(assistantMessage.content),
        cost: "0",
        tool_calls: assistantMessage.tool_calls || undefined,
      }
    : null;

  const tools = extractTools(filteredInputMessages, spanData.raw_data);

  // Create the prompt object
  const prompt: PromptType = {
    id: `span-prompt-${spanData.id}-${Date.now()}`,
    classification: promptClassificationEnum.DEFAULT,
    name: `Span: ${spanData.span_name || spanData.span_id || "Unknown"}`,
    created_at: spanData.created_at,
    modelName,
    modelProvider,
    messages: filteredInputMessages,
    modelParameters,
    runResponse: runResponse,
    responseFormat: undefined,
    tools,
    toolChoice: tools.length > 0 ? "auto" : undefined,
  };

  return prompt;
};

export default apiToFrontendPrompt;
