/**
 * Utility functions for setting OpenTelemetry span attributes
 */

import type {
  AnyAISpan,
  LLMGenerationAttributes,
  AgentRunAttributes,
  LLMChunkAttributes,
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
  errorInfo: AnyAISpan["errorInfo"]
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

export function setSpanAttributes(otelSpan: OISpan, span: AnyAISpan): void {
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
    case AISpanType.LLM_GENERATION:
      additionalAttributes = setLLMGenerationAttributes(otelSpan, span);
      break;
    case AISpanType.LLM_CHUNK:
      additionalAttributes = setLLMChunkAttributes(otelSpan, span);
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

export function getOpenInferenceSpanKind(span: AnyAISpan): string {
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
    case AISpanType.LLM_GENERATION:
    case AISpanType.LLM_CHUNK:
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

function setInputOutputAttributes(otelSpan: OISpan, span: AnyAISpan): void {
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
    if (typeof span.input === "string") {
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
  metadata: AnyAISpan["metadata"]
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

// Attribute handler functions for each AISpanType
function setAgentRunAttributes(
  otelSpan: OISpan,
  span: AnyAISpan
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

function setLLMGenerationAttributes(
  otelSpan: OISpan,
  span: AnyAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const llmAttr = span.attributes as LLMGenerationAttributes;
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

  // Return any additional attributes to be added to metadata
  return additionalAttributes;
}

function setLLMChunkAttributes(
  otelSpan: OISpan,
  span: AnyAISpan
): Record<string, unknown> {
  const additionalAttributes: Record<string, unknown> = {};
  const attr = span.attributes as LLMChunkAttributes;
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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
  span: AnyAISpan
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

function setRetrieverAttributes(otelSpan: OISpan, span: AnyAISpan): void {
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
