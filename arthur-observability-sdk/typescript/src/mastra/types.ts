/**
 * Local type declarations for @mastra/core/ai-tracing types.
 * These mirror the Mastra types so the SDK compiles without @mastra/core installed.
 * At runtime, the actual @mastra/core types are used via the peer dependency.
 */

export interface AnyExportedAISpan {
  id: string;
  traceId: string;
  parentSpanId?: string;
  name: string;
  type: string;
  startTime: Date;
  endTime?: Date;
  input?: any;
  output?: any;
  attributes: Record<string, any>;
  metadata?: Record<string, any>;
  errorInfo?: any;
  isEvent?: boolean;
}

export interface AITracingEvent {
  type: "span_started" | "span_updated" | "span_ended";
  exportedSpan: AnyExportedAISpan;
}

export interface AITracingExporter {
  name: string;
  exportEvent(event: AITracingEvent): Promise<void>;
  shutdown(): Promise<void>;
}

export interface ModelGenerationAttributes {
  model?: string;
  provider?: string;
  resultType?: string;
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
    promptCacheHitTokens?: number;
    promptCacheMissTokens?: number;
  };
  parameters?: Record<string, any>;
  streaming?: boolean;
  finishReason?: string;
}

export interface AgentRunAttributes {
  agentId?: string;
  prompt?: string;
  instructions?: string;
  availableTools?: any[];
  maxSteps?: number;
}

export interface ModelChunkAttributes {
  chunkType?: string;
  sequenceNumber?: number;
}

export interface ToolCallAttributes {
  toolId?: string;
  toolType?: string;
  toolDescription?: string;
  success?: boolean;
}

export interface MCPToolCallAttributes {
  toolId?: string;
  mcpServer?: string;
  serverVersion?: string;
  success?: boolean;
}

export interface WorkflowRunAttributes {
  workflowId?: string;
  status?: string;
}

export interface WorkflowStepAttributes {
  stepId?: string;
  status?: string;
}

export interface WorkflowConditionalAttributes {
  conditionCount?: number;
  truthyIndexes?: number[];
  selectedSteps?: string[];
}

export interface WorkflowConditionalEvalAttributes {
  conditionIndex?: number;
  result?: boolean;
}

export interface WorkflowParallelAttributes {
  branchCount?: number;
  parallelSteps?: string[];
}

export interface WorkflowLoopAttributes {
  loopType?: string;
  iteration?: number;
  totalIterations?: number;
  concurrency?: number;
}

export interface WorkflowSleepAttributes {
  durationMs?: number;
  untilDate?: Date;
  sleepType?: string;
}

export interface WorkflowWaitEventAttributes {
  eventName?: string;
  timeoutMs?: number;
  eventReceived?: boolean;
  waitDurationMs?: number;
}

/**
 * Mastra AI span type enum values (matches @mastra/core/ai-tracing AISpanType)
 */
export const AISpanType = {
  AGENT_RUN: "agent_run",
  MODEL_GENERATION: "model_generation",
  MODEL_CHUNK: "model_chunk",
  TOOL_CALL: "tool_call",
  MCP_TOOL_CALL: "mcp_tool_call",
  WORKFLOW_RUN: "workflow_run",
  WORKFLOW_STEP: "workflow_step",
  WORKFLOW_CONDITIONAL: "workflow_conditional",
  WORKFLOW_CONDITIONAL_EVAL: "workflow_conditional_eval",
  WORKFLOW_PARALLEL: "workflow_parallel",
  WORKFLOW_LOOP: "workflow_loop",
  WORKFLOW_SLEEP: "workflow_sleep",
  WORKFLOW_WAIT_EVENT: "workflow_wait_event",
  GENERIC: "generic",
} as const;
