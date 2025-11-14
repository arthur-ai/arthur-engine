/**
 * Utility functions for setting OpenTelemetry span attributes
 */

import type {
  AnyExportedAISpan,
  ModelGenerationAttributes,
  AgentRunAttributes,
  ModelChunkAttributes,
  ToolCallAttributes,
  MCPToolCallAttributes,
  WorkflowRunAttributes,
  WorkflowStepAttributes,
  WorkflowConditionalAttributes,
  WorkflowConditionalEvalAttributes,
  WorkflowParallelAttributes,
  WorkflowLoopAttributes,
  WorkflowSleepAttributes,
  WorkflowWaitEventAttributes,
} from "@mastra/core/ai-tracing";
import { AISpanType } from "@mastra/core/ai-tracing";
import { AttributeValue, SpanStatusCode } from "@opentelemetry/api";
import {
  MimeType,
  OpenInferenceSpanKind,
  SemanticConventions,
} from "@arizeai/openinference-semantic-conventions";
import { OISpan } from "@arizeai/openinference-core";

export function setSpanErrorInfo(
  otelSpan: OISpan,
  errorInfo: AnyExportedAISpan["errorInfo"]
): void {
  if (errorInfo) {
    otelSpan.setStatus({
      code: SpanStatusCode.ERROR,
      message: JSON.stringify(errorInfo),
    });
  } else {
    otelSpan.setStatus({ code: SpanStatusCode.OK });
  }
}

export function setSpanAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): void {
  // Set OpenInference span kind
  const openInferenceSpanKind = getOpenInferenceSpanKind(span);
  otelSpan.setAttributes({
    [SemanticConventions.OPENINFERENCE_SPAN_KIND]: openInferenceSpanKind,
  });

  // set the generic AIAnySpan attributes
  setInputOutputAttributes(otelSpan, span);

  // set the span-type specific attributes and collect any additional attributes
  let additionalAttributes: Record<string, unknown> = {};

  // special case for RAG spans that mastra doesn't yet support
  if (openInferenceSpanKind === OpenInferenceSpanKind.RETRIEVER) {
    setRetrieverAttributes(otelSpan, span);
  }

  switch (span.type) {
    case AISpanType.AGENT_RUN:
      additionalAttributes = setAgentRunAttributes(otelSpan, span);
      break;
    case AISpanType.MODEL_GENERATION:
      additionalAttributes = setModelGenerationAttributes(otelSpan, span);
      break;
    case AISpanType.MODEL_CHUNK:
      additionalAttributes = setModelChunkAttributes(otelSpan, span);
      break;
    case AISpanType.TOOL_CALL:
      additionalAttributes = setToolCallAttributes(otelSpan, span);
      break;
    case AISpanType.MCP_TOOL_CALL:
      additionalAttributes = setMCPToolCallAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_RUN:
      additionalAttributes = setWorkflowRunAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_STEP:
      additionalAttributes = setWorkflowStepAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_CONDITIONAL:
      additionalAttributes = setWorkflowConditionalAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_CONDITIONAL_EVAL:
      additionalAttributes = setWorkflowConditionalEvalAttributes(
        otelSpan,
        span
      );
      break;
    case AISpanType.WORKFLOW_PARALLEL:
      additionalAttributes = setWorkflowParallelAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_LOOP:
      additionalAttributes = setWorkflowLoopAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_SLEEP:
      additionalAttributes = setWorkflowSleepAttributes(otelSpan, span);
      break;
    case AISpanType.WORKFLOW_WAIT_EVENT:
      additionalAttributes = setWorkflowWaitEventAttributes(otelSpan, span);
      break;
    // Generic spans have no specific attributes
    // case AISpanType.GENERIC:
    //   break;
  }

  // Merge additional attributes with existing metadata
  const mergedMetadata = {
    ...span.metadata,
    ...additionalAttributes,
  };

  setMetadataAttributes(otelSpan, mergedMetadata);
}

export function getOpenInferenceSpanKind(span: AnyExportedAISpan): string {
  // Mastra doesn't have a retriever span yet, so work around it with naming
  if (
    span.type === AISpanType.GENERIC &&
    span.name.toLowerCase().includes("rag")
  ) {
    return OpenInferenceSpanKind.RETRIEVER;
  }

  switch (span.type) {
    case AISpanType.AGENT_RUN:
      return OpenInferenceSpanKind.AGENT;

    // all map to LLM in OpenInference
    case AISpanType.MODEL_GENERATION:
      return OpenInferenceSpanKind.LLM;

    // all map to TOOL in OpenInference
    case AISpanType.TOOL_CALL:
    case AISpanType.MCP_TOOL_CALL:
      return OpenInferenceSpanKind.TOOL;

    // all map to CHAIN in OpenInference
    case AISpanType.WORKFLOW_RUN:
    case AISpanType.WORKFLOW_STEP:
    case AISpanType.WORKFLOW_CONDITIONAL:
    case AISpanType.WORKFLOW_CONDITIONAL_EVAL:
    case AISpanType.WORKFLOW_PARALLEL:
    case AISpanType.WORKFLOW_LOOP:
    case AISpanType.WORKFLOW_SLEEP:
    case AISpanType.WORKFLOW_WAIT_EVENT:
    case AISpanType.GENERIC:
    default: // Default to CHAIN for unknown types
      return OpenInferenceSpanKind.CHAIN;
  }
}

function setInputOutputAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): void {
  // set input
  if (span.input) {
    if (typeof span.input === "string") {
      otelSpan.setAttributes({
        [SemanticConventions.INPUT_MIME_TYPE]: MimeType.TEXT,
        [SemanticConventions.INPUT_VALUE]: span.input,
      });
    } else {
      otelSpan.setAttributes({
        [SemanticConventions.INPUT_MIME_TYPE]: MimeType.JSON,
        [SemanticConventions.INPUT_VALUE]: JSON.stringify(span.input),
      });
    }
  }
  // set output
  if (span.output) {
    if (typeof span.output === "string") {
      otelSpan.setAttributes({
        [SemanticConventions.OUTPUT_MIME_TYPE]: MimeType.TEXT,
        [SemanticConventions.OUTPUT_VALUE]: span.output,
      });
    } else {
      otelSpan.setAttributes({
        [SemanticConventions.OUTPUT_MIME_TYPE]: MimeType.JSON,
        [SemanticConventions.OUTPUT_VALUE]: JSON.stringify(span.output),
      });
    }
  }
}

function setMetadataAttributes(
  otelSpan: OISpan,
  metadata: AnyExportedAISpan["metadata"]
): void {
  // set metadata based attributes
  const { userId, sessionId, ...remainingMetadata } = metadata ?? {};

  // set sessionId
  if (sessionId) {
    otelSpan.setAttributes({
      [SemanticConventions.SESSION_ID]: sessionId,
    });
  }
  // set userId
  if (userId) {
    otelSpan.setAttributes({
      [SemanticConventions.USER_ID]: userId,
    });
  }
  // set metadata
  if (remainingMetadata) {
    otelSpan.setAttributes({
      [SemanticConventions.METADATA]: JSON.stringify(remainingMetadata),
    });
  }
}

/**
 * Constructs LLM input and output messages from span input/output data
 * following OpenInference semantic conventions and sets them on the OpenTelemetry span
 */
function constructLLMMessages(otelSpan: OISpan, span: AnyExportedAISpan): void {
  // Process input messages
  if (span.input) {
    const inputMessages = extractMessagesFromData(span.input);
    if (inputMessages.length > 0) {
      const inputMessageAttributes = {
        [SemanticConventions.LLM_INPUT_MESSAGES]: inputMessages,
      };
      const flattenedInput = flattenAttributes(inputMessageAttributes);
      otelSpan.setAttributes(flattenedInput);
    }
  }

  // Process output messages
  if (span.output) {
    // For output, wrap the entire output as a single assistant message
    const outputMessage = wrapOutputAsMessage(span.output);
    if (outputMessage) {
      const outputMessageAttributes = {
        [SemanticConventions.LLM_OUTPUT_MESSAGES]: [outputMessage],
      };
      const flattenedOutput = flattenAttributes(outputMessageAttributes);
      otelSpan.setAttributes(flattenedOutput);
    }
  }
}

/**
 * Wraps output data as a single assistant message
 */
function wrapOutputAsMessage(output: unknown): Record<string, unknown> | null {
  if (output === null || output === undefined) {
    return null;
  }

  const message: Record<string, unknown> = {
    [SemanticConventions.MESSAGE_ROLE]: "assistant",
  };

  // Handle different output formats
  if (typeof output === "string") {
    message[SemanticConventions.MESSAGE_CONTENT] = output;
  } else if (isObject(output)) {
    // If it's already a message-like object, preserve its structure
    if (output.role) {
      message[SemanticConventions.MESSAGE_ROLE] = output.role;
    }
    if (output.content !== undefined) {
      message[SemanticConventions.MESSAGE_CONTENT] = output.content;
    } else if (output.contents !== undefined) {
      message[SemanticConventions.MESSAGE_CONTENTS] = output.contents;
    } else {
      // If no content/contents, JSON serialize the entire object as content
      message[SemanticConventions.MESSAGE_CONTENT] = JSON.stringify(output);
    }

    // Preserve other message properties
    if (output.name) {
      message[SemanticConventions.MESSAGE_NAME] = output.name;
    }
    if (output.tool_calls) {
      message[SemanticConventions.MESSAGE_TOOL_CALLS] = output.tool_calls;
    }
    if (output.tool_call_id) {
      message[SemanticConventions.MESSAGE_TOOL_CALL_ID] = output.tool_call_id;
    }
    if (output.function_call && isObject(output.function_call)) {
      const funcCall = output.function_call as Record<string, unknown>;
      if (funcCall.name) {
        message[SemanticConventions.MESSAGE_FUNCTION_CALL_NAME] = funcCall.name;
      }
      if (funcCall.arguments) {
        message[SemanticConventions.MESSAGE_FUNCTION_CALL_ARGUMENTS_JSON] =
          JSON.stringify(funcCall.arguments);
      }
    }
  } else {
    // For other types (numbers, booleans, etc.), convert to string content
    message[SemanticConventions.MESSAGE_CONTENT] = String(output);
  }

  return message;
}

/**
 * Extracts messages from various input/output data formats
 */
function extractMessagesFromData(
  data: unknown
): Array<Record<string, unknown>> {
  const messages: Array<Record<string, unknown>> = [];

  if (Array.isArray(data)) {
    // Handle array of messages
    data.forEach((item) => {
      const message = extractMessageFromItem(item);
      if (message) {
        messages.push(message);
      }
    });
  } else if (isObject(data)) {
    // Handle single message object
    const message = extractMessageFromItem(data);
    if (message) {
      messages.push(message);
    } else if (data.messages && Array.isArray(data.messages)) {
      // Handle object with messages array
      data.messages.forEach((item: unknown) => {
        const message = extractMessageFromItem(item);
        if (message) {
          messages.push(message);
        }
      });
    } else if (data.content || data.role) {
      // Handle direct message properties
      const message = extractMessageFromItem(data);
      if (message) {
        messages.push(message);
      }
    }
  } else if (typeof data === "string") {
    // Handle string input as user message
    messages.push({
      [SemanticConventions.MESSAGE_ROLE]: "user",
      [SemanticConventions.MESSAGE_CONTENT]: data,
    });
  }

  return messages;
}

/**
 * Extracts a single message from an item, handling various formats
 */
function extractMessageFromItem(item: unknown): Record<string, unknown> | null {
  if (!isObject(item)) {
    return null;
  }

  const message: Record<string, unknown> = {};

  // Extract role
  if (item.role) {
    message[SemanticConventions.MESSAGE_ROLE] = item.role;
  } else if (item.type) {
    // Some formats use 'type' instead of 'role'
    message[SemanticConventions.MESSAGE_ROLE] = item.type;
  } else {
    // Default to 'user' if no role specified
    message[SemanticConventions.MESSAGE_ROLE] = "user";
  }

  // Extract content
  if (item.content !== undefined) {
    if (typeof item.content === "string") {
      message[SemanticConventions.MESSAGE_CONTENT] = item.content;
    } else if (
      Array.isArray(item.content) &&
      item.content.length === 1 &&
      isObject(item.content[0]) &&
      typeof item.content[0].text === "string"
    ) {
      // if there is a single text content incorrectly formatted as an array, extract just the text string to adhere to open inference formatting
      message[SemanticConventions.MESSAGE_CONTENT] = item.content[0].text;
    } else {
      // fail safe if content doesn't match any expected formatting
      message[SemanticConventions.MESSAGE_CONTENT] = JSON.stringify(
        item.content
      );
    }
  } else if (item.contents !== undefined) {
    // Handle contents array (multimodal content)
    message[SemanticConventions.MESSAGE_CONTENTS] = item.contents;
  } else if (item.text !== undefined) {
    message[SemanticConventions.MESSAGE_CONTENT] = item.text;
  } else if (item.message !== undefined) {
    message[SemanticConventions.MESSAGE_CONTENT] = item.message;
  } else if (typeof item === "string") {
    message[SemanticConventions.MESSAGE_CONTENT] = item;
  }

  // Extract additional message properties
  if (item.name) {
    message[SemanticConventions.MESSAGE_NAME] = item.name;
  }
  if (item.tool_calls) {
    message[SemanticConventions.MESSAGE_TOOL_CALLS] = item.tool_calls;
  }
  if (item.tool_call_id) {
    message[SemanticConventions.MESSAGE_TOOL_CALL_ID] = item.tool_call_id;
  }
  if (item.function_call && isObject(item.function_call)) {
    const funcCall = item.function_call as Record<string, unknown>;
    if (funcCall.name) {
      message[SemanticConventions.MESSAGE_FUNCTION_CALL_NAME] = funcCall.name;
    }
    if (funcCall.arguments) {
      message[SemanticConventions.MESSAGE_FUNCTION_CALL_ARGUMENTS_JSON] =
        JSON.stringify(funcCall.arguments);
    }
  }

  // Only return message if it has content or contents
  return message[SemanticConventions.MESSAGE_CONTENT] !== undefined ||
    message[SemanticConventions.MESSAGE_CONTENTS] !== undefined
    ? message
    : null;
}

// Attribute handler functions for each AISpanType
function setAgentRunAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as AgentRunAttributes;
  if (attr) {
    if (attr.agentId) {
      otelSpan.setAttributes({
        [SemanticConventions.AGENT_NAME]: attr.agentId,
      });
    }

    // AFAICT attr.prompt is never set
    const agentPrompt = attr.prompt ?? attr.instructions;
    if (agentPrompt) {
      additionalAttributes["agent.instructions"] = agentPrompt;
    }

    if (attr.availableTools) {
      additionalAttributes["agent.available_tools"] = JSON.stringify(
        attr.availableTools
      );
    }
    if (attr.maxSteps) {
      additionalAttributes["agent.max_steps"] = attr.maxSteps;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setModelGenerationAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const llmAttr = span.attributes as ModelGenerationAttributes;
  if (llmAttr) {
    if (llmAttr.model) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_MODEL_NAME]: llmAttr.model,
      });
    }
    if (llmAttr.provider) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_PROVIDER]: llmAttr.provider,
      });
    }
    if (llmAttr.resultType) {
      additionalAttributes["result_type"] = llmAttr.resultType;
    }
    if (llmAttr.usage?.promptTokens) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_TOKEN_COUNT_PROMPT]:
          llmAttr.usage.promptTokens,
      });
    }
    if (llmAttr.usage?.completionTokens) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_TOKEN_COUNT_COMPLETION]:
          llmAttr.usage.completionTokens,
      });
    }
    if (llmAttr.usage?.totalTokens) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_TOKEN_COUNT_TOTAL]: llmAttr.usage.totalTokens,
      });
    }
    if (llmAttr.usage?.promptCacheHitTokens) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_READ]:
          llmAttr.usage.promptCacheHitTokens,
      });
    }
    if (llmAttr.usage?.promptCacheMissTokens) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_WRITE]:
          llmAttr.usage.promptCacheMissTokens,
      });
    }
    if (llmAttr.parameters) {
      otelSpan.setAttributes({
        [SemanticConventions.LLM_INVOCATION_PARAMETERS]: JSON.stringify(
          llmAttr.parameters
        ),
      });
    }
    if (llmAttr.streaming !== undefined) {
      additionalAttributes["streaming"] = llmAttr.streaming;
    }
    if (llmAttr.finishReason) {
      additionalAttributes["finish_reason"] = llmAttr.finishReason;
    }
  }

  // Construct LLM input and output messages from span input/output
  constructLLMMessages(otelSpan, span);

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setModelChunkAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as ModelChunkAttributes;
  if (attr) {
    if (attr.chunkType) {
      additionalAttributes["chunk_type"] = attr.chunkType;
    }
    if (attr.sequenceNumber !== undefined) {
      additionalAttributes["sequence_number"] = attr.sequenceNumber;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setToolCallAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as ToolCallAttributes;
  if (attr) {
    if (attr.toolId) {
      otelSpan.setAttributes({
        [SemanticConventions.TOOL_CALL_FUNCTION_NAME]: attr.toolId,
      });
    }
    if (attr.toolType) {
      additionalAttributes["tool.type"] = attr.toolType;
    }
    if (attr.toolDescription) {
      otelSpan.setAttributes({
        [SemanticConventions.TOOL_DESCRIPTION]: attr.toolDescription,
      });
    }
    if (attr.success !== undefined) {
      additionalAttributes["tool.success"] = attr.success;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setMCPToolCallAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as MCPToolCallAttributes;
  if (attr) {
    if (attr.toolId) {
      otelSpan.setAttributes({
        [SemanticConventions.TOOL_CALL_FUNCTION_NAME]: attr.toolId,
      });
    }
    if (attr.mcpServer) {
      additionalAttributes["mcp.server"] = attr.mcpServer;
    }
    if (attr.serverVersion) {
      additionalAttributes["mcp.server_version"] = attr.serverVersion;
    }
    if (attr.success !== undefined) {
      additionalAttributes["mcp.success"] = attr.success;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowRunAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowRunAttributes;
  if (attr) {
    if (attr.workflowId) {
      additionalAttributes["workflow.id"] = attr.workflowId;
    }
    if (attr.status) {
      additionalAttributes["workflow.status"] = attr.status;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowStepAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowStepAttributes;
  if (attr) {
    if (attr.stepId) {
      additionalAttributes["workflow.step_id"] = attr.stepId;
    }
    if (attr.status) {
      additionalAttributes["workflow.step_status"] = attr.status;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowConditionalAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowConditionalAttributes;
  if (attr) {
    if (attr.conditionCount !== undefined) {
      additionalAttributes["workflow.condition_count"] = attr.conditionCount;
    }
    if (attr.truthyIndexes) {
      additionalAttributes["workflow.truthy_indexes"] = JSON.stringify(
        attr.truthyIndexes
      );
    }
    if (attr.selectedSteps) {
      additionalAttributes["workflow.selected_steps"] = JSON.stringify(
        attr.selectedSteps
      );
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowConditionalEvalAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowConditionalEvalAttributes;
  if (attr) {
    if (attr.conditionIndex !== undefined) {
      additionalAttributes["workflow.condition_index"] = attr.conditionIndex;
    }
    if (attr.result !== undefined) {
      additionalAttributes["workflow.condition_result"] = attr.result;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowParallelAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowParallelAttributes;
  if (attr) {
    if (attr.branchCount !== undefined) {
      additionalAttributes["workflow.branch_count"] = attr.branchCount;
    }
    if (attr.parallelSteps) {
      additionalAttributes["workflow.parallel_steps"] = JSON.stringify(
        attr.parallelSteps
      );
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowLoopAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowLoopAttributes;
  if (attr) {
    if (attr.loopType) {
      additionalAttributes["workflow.loop_type"] = attr.loopType;
    }
    if (attr.iteration !== undefined) {
      additionalAttributes["workflow.iteration"] = attr.iteration;
    }
    if (attr.totalIterations !== undefined) {
      additionalAttributes["workflow.total_iterations"] = attr.totalIterations;
    }
    if (attr.concurrency !== undefined) {
      additionalAttributes["workflow.concurrency"] = attr.concurrency;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowSleepAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowSleepAttributes;
  if (attr) {
    if (attr.durationMs !== undefined) {
      additionalAttributes["workflow.sleep_duration_ms"] = attr.durationMs;
    }
    if (attr.untilDate) {
      additionalAttributes["workflow.sleep_until_date"] =
        attr.untilDate.toISOString();
    }
    if (attr.sleepType) {
      additionalAttributes["workflow.sleep_type"] = attr.sleepType;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setWorkflowWaitEventAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as WorkflowWaitEventAttributes;
  if (attr) {
    if (attr.eventName) {
      additionalAttributes["workflow.event_name"] = attr.eventName;
    }
    if (attr.timeoutMs !== undefined) {
      additionalAttributes["workflow.timeout_ms"] = attr.timeoutMs;
    }
    if (attr.eventReceived !== undefined) {
      additionalAttributes["workflow.event_received"] = attr.eventReceived;
    }
    if (attr.waitDurationMs !== undefined) {
      additionalAttributes["workflow.wait_duration_ms"] = attr.waitDurationMs;
    }
  }

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setRetrieverAttributes(
  otelSpan: OISpan,
  span: AnyExportedAISpan
): void {
  // if the span.output is an object and it has the property "results", and results is an array,
  // iterate over each result setting
  if (
    span.output &&
    typeof span.output === "object" &&
    span.output.results &&
    Array.isArray(span.output.results)
  ) {
    // for each result, construct a document object with the following properties:
    // - id
    // - content
    // - metadata
    // - score
    const documents = span.output.results.map(
      (result: Record<string, unknown>) => {
        return {
          [SemanticConventions.DOCUMENT_ID]: result.id,
          [SemanticConventions.DOCUMENT_CONTENT]: result.content
            ? JSON.stringify(result.content)
            : undefined,
          [SemanticConventions.DOCUMENT_METADATA]: result.metadata
            ? JSON.stringify(result.metadata)
            : undefined,
          [SemanticConventions.DOCUMENT_SCORE]: (
            result.metadata as Record<string, unknown>
          )?.distance,
        };
      }
    );

    const flattenedDocuments = flattenAttributes({
      [SemanticConventions.RETRIEVAL_DOCUMENTS]: documents,
    });
    otelSpan.setAttributes(flattenedDocuments);
  }
}

// taken from openinference-instrumentation-langchain

/**
 * A type-guard function for checking if a value is an object
 */
export function isObject(
  value: unknown
): value is Record<string | number | symbol, unknown> {
  return typeof value === "object" && value != null && !Array.isArray(value);
}

/**
 * Flattens a nested object into a single level object with keys as dot-separated paths.
 * Specifies elements in arrays with their index as part of the path.
 * @param attributes - Nested attributes to flatten.
 * @param baseKey - Base key to prepend to all keys.
 * @returns Flattened attributes
 */
function flattenAttributes(
  attributes: Record<string, unknown>,
  baseKey: string = ""
): Record<string, AttributeValue> {
  const result: Record<string, AttributeValue> = {};
  for (const key in attributes) {
    const newKey = baseKey ? `${baseKey}.${key}` : key;
    const value = attributes[key];

    if (value == null) {
      continue;
    }

    if (isObject(value)) {
      Object.assign(result, flattenAttributes(value, newKey));
    } else if (Array.isArray(value)) {
      value.forEach((item, index) => {
        if (isObject(item)) {
          Object.assign(result, flattenAttributes(item, `${newKey}.${index}`));
        } else {
          result[`${newKey}.${index}`] = item;
        }
      });
    } else if (
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "boolean"
    ) {
      result[newKey] = value;
    }
  }
  return result;
}
