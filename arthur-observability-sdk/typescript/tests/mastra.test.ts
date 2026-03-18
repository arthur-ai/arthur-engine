import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock @mastra/core/ai-tracing
vi.mock("@mastra/core/ai-tracing", () => ({
  AISpanType: {
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
  },
}));

// Mock OTel exporter and provider
const mockExporter = { shutdown: vi.fn() };
const mockEnd = vi.fn();
const mockSetAttributes = vi.fn();
const mockSetStatus = vi.fn();
const mockStartSpan = vi.fn(() => ({
  end: mockEnd,
  setAttributes: mockSetAttributes,
  setStatus: mockSetStatus,
  setAttribute: vi.fn(),
  spanContext: () => ({ traceId: "trace-1", spanId: "span-1" }),
}));
const mockGetTracer = vi.fn(() => ({
  startSpan: mockStartSpan,
  startActiveSpan: vi.fn(),
}));
const mockProviderShutdown = vi.fn(() => Promise.resolve());

vi.mock("@opentelemetry/exporter-trace-otlp-proto", () => ({
  OTLPTraceExporter: vi.fn(() => mockExporter),
}));

vi.mock("@opentelemetry/sdk-trace-node", () => ({
  NodeTracerProvider: vi.fn(() => ({
    getTracer: mockGetTracer,
    shutdown: mockProviderShutdown,
  })),
}));

vi.mock("@opentelemetry/sdk-trace-base", () => ({
  BatchSpanProcessor: vi.fn(),
}));

vi.mock("@opentelemetry/resources", () => ({
  Resource: vi.fn((attrs: any) => attrs),
}));

vi.mock("@arizeai/openinference-core", () => ({
  OITracer: vi.fn().mockImplementation(() => ({
    startSpan: mockStartSpan,
  })),
  OISpan: vi.fn(),
}));

vi.mock("@arizeai/openinference-semantic-conventions", () => ({
  MimeType: { TEXT: "text/plain", JSON: "application/json" },
  OpenInferenceSpanKind: {
    AGENT: "AGENT",
    LLM: "LLM",
    TOOL: "TOOL",
    CHAIN: "CHAIN",
    RETRIEVER: "RETRIEVER",
  },
  SemanticConventions: {
    OPENINFERENCE_SPAN_KIND: "openinference.span.kind",
    INPUT_MIME_TYPE: "input.mime_type",
    INPUT_VALUE: "input.value",
    OUTPUT_MIME_TYPE: "output.mime_type",
    OUTPUT_VALUE: "output.value",
    SESSION_ID: "session.id",
    USER_ID: "user.id",
    METADATA: "metadata",
    AGENT_NAME: "agent.name",
    LLM_MODEL_NAME: "llm.model_name",
    LLM_PROVIDER: "llm.provider",
    LLM_TOKEN_COUNT_PROMPT: "llm.token_count.prompt",
    LLM_TOKEN_COUNT_COMPLETION: "llm.token_count.completion",
    LLM_TOKEN_COUNT_TOTAL: "llm.token_count.total",
    LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_READ:
      "llm.token_count.prompt_details.cache_read",
    LLM_TOKEN_COUNT_PROMPT_DETAILS_CACHE_WRITE:
      "llm.token_count.prompt_details.cache_write",
    LLM_INVOCATION_PARAMETERS: "llm.invocation_parameters",
    LLM_INPUT_MESSAGES: "llm.input_messages",
    LLM_OUTPUT_MESSAGES: "llm.output_messages",
    TOOL_CALL_FUNCTION_NAME: "tool.call.function.name",
    TOOL_DESCRIPTION: "tool.description",
    MESSAGE_ROLE: "message.role",
    MESSAGE_CONTENT: "message.content",
    MESSAGE_CONTENTS: "message.contents",
    MESSAGE_NAME: "message.name",
    MESSAGE_TOOL_CALLS: "message.tool_calls",
    MESSAGE_TOOL_CALL_ID: "message.tool_call_id",
    MESSAGE_FUNCTION_CALL_NAME: "message.function_call_name",
    MESSAGE_FUNCTION_CALL_ARGUMENTS_JSON:
      "message.function_call_arguments_json",
    DOCUMENT_ID: "document.id",
    DOCUMENT_CONTENT: "document.content",
    DOCUMENT_METADATA: "document.metadata",
    DOCUMENT_SCORE: "document.score",
    RETRIEVAL_DOCUMENTS: "retrieval.documents",
  },
}));

import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { ArthurExporter } from "../src/mastra";
import type { ArthurExporterConfig } from "../src/mastra";

function makeConfig(
  overrides?: Partial<ArthurExporterConfig>,
): ArthurExporterConfig {
  return {
    url: "http://localhost:3030",
    apiKey: "test-api-key",
    taskId: "task-123",
    serviceName: "test-svc",
    ...overrides,
  };
}

describe("ArthurExporter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("constructor", () => {
    it("creates OTLPTraceExporter with correct endpoint and auth headers", () => {
      new ArthurExporter(makeConfig());
      expect(OTLPTraceExporter).toHaveBeenCalledWith({
        url: "http://localhost:3030/api/v1/traces",
        headers: {
          Authorization: "Bearer test-api-key",
        },
      });
    });

    it("strips trailing slash from url", () => {
      new ArthurExporter(makeConfig({ url: "http://localhost:3030/" }));
      expect(OTLPTraceExporter).toHaveBeenCalledWith(
        expect.objectContaining({
          url: "http://localhost:3030/api/v1/traces",
        }),
      );
    });

    it("merges custom headers with auth header", () => {
      new ArthurExporter(
        makeConfig({ headers: { "X-Custom": "value" } }),
      );
      expect(OTLPTraceExporter).toHaveBeenCalledWith({
        url: "http://localhost:3030/api/v1/traces",
        headers: {
          Authorization: "Bearer test-api-key",
          "X-Custom": "value",
        },
      });
    });

    it("has name property set to 'arthur'", () => {
      const exporter = new ArthurExporter(makeConfig());
      expect(exporter.name).toBe("arthur");
    });
  });

  describe("exportEvent", () => {
    it("creates a span on span_started", async () => {
      const exporter = new ArthurExporter(makeConfig());
      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "span-1",
          traceId: "trace-1",
          name: "agent-run",
          type: "agent_run" as any,
          startTime: new Date(),
          attributes: {},
          isEvent: false,
        } as any,
      });
      expect(mockStartSpan).toHaveBeenCalledWith(
        "agent-run",
        expect.any(Object),
        expect.anything(),
      );
    });

    it("ends a span on span_ended", async () => {
      const exporter = new ArthurExporter(makeConfig());
      const endTime = new Date();

      // Start then end
      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "span-1",
          traceId: "trace-1",
          name: "agent-run",
          type: "agent_run" as any,
          startTime: new Date(),
          attributes: {},
          isEvent: false,
        } as any,
      });

      await exporter.exportEvent({
        type: "span_ended",
        exportedSpan: {
          id: "span-1",
          traceId: "trace-1",
          name: "agent-run",
          type: "agent_run" as any,
          startTime: new Date(),
          endTime,
          attributes: {},
          isEvent: false,
        } as any,
      });

      expect(mockEnd).toHaveBeenCalledWith(endTime);
    });

    it("updates attributes on span_updated", async () => {
      const exporter = new ArthurExporter(makeConfig());

      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "span-1",
          traceId: "trace-1",
          name: "model-gen",
          type: "model_generation" as any,
          startTime: new Date(),
          attributes: { model: "gpt-4" },
          isEvent: false,
        } as any,
      });

      // Clear calls from start
      mockSetAttributes.mockClear();

      await exporter.exportEvent({
        type: "span_updated",
        exportedSpan: {
          id: "span-1",
          traceId: "trace-1",
          name: "model-gen",
          type: "model_generation" as any,
          startTime: new Date(),
          attributes: {
            model: "gpt-4",
            usage: { promptTokens: 10, completionTokens: 20, totalTokens: 30 },
          },
          isEvent: false,
        } as any,
      });

      expect(mockSetAttributes).toHaveBeenCalled();
    });

    it("handles event spans (isEvent=true) — creates and ends immediately", async () => {
      const exporter = new ArthurExporter(makeConfig());

      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "event-1",
          traceId: "trace-1",
          name: "some-event",
          type: "generic" as any,
          startTime: new Date(),
          attributes: {},
          isEvent: true,
        } as any,
      });

      // Event spans end immediately with no args
      expect(mockEnd).toHaveBeenCalled();
    });

    it("handles parent-child span relationships via parentSpanId", async () => {
      const exporter = new ArthurExporter(makeConfig());

      // Create parent span
      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "parent-1",
          traceId: "trace-1",
          name: "agent-run",
          type: "agent_run" as any,
          startTime: new Date(),
          attributes: {},
          isEvent: false,
        } as any,
      });

      // Create child span with parentSpanId
      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "child-1",
          traceId: "trace-1",
          parentSpanId: "parent-1",
          name: "model-gen",
          type: "model_generation" as any,
          startTime: new Date(),
          attributes: {},
          isEvent: false,
        } as any,
      });

      // The second startSpan call should have a parent context (not ROOT_CONTEXT)
      // We verify by checking that startSpan was called twice
      expect(mockStartSpan).toHaveBeenCalledTimes(2);
    });

    it("does not throw on errors during export", async () => {
      const exporter = new ArthurExporter(makeConfig());
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      mockStartSpan.mockImplementationOnce(() => {
        throw new Error("boom");
      });

      await expect(
        exporter.exportEvent({
          type: "span_started",
          exportedSpan: {
            id: "span-1",
            traceId: "trace-1",
            name: "test",
            type: "generic" as any,
            startTime: new Date(),
            attributes: {},
            isEvent: false,
          } as any,
        }),
      ).resolves.not.toThrow();

      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe("shutdown", () => {
    it("ends remaining spans and shuts down provider", async () => {
      const exporter = new ArthurExporter(makeConfig());

      // Start a span but don't end it
      await exporter.exportEvent({
        type: "span_started",
        exportedSpan: {
          id: "orphan-1",
          traceId: "trace-1",
          name: "orphan",
          type: "generic" as any,
          startTime: new Date(),
          attributes: {},
          isEvent: false,
        } as any,
      });

      await exporter.shutdown();

      // The orphan span should be ended
      expect(mockEnd).toHaveBeenCalled();
      // Provider should be shut down
      expect(mockProviderShutdown).toHaveBeenCalled();
    });
  });
});

describe("getOpenInferenceSpanKind (via setSpanAttributes)", () => {
  // We test span kind mapping indirectly through setSpanAttributes calls
  // by checking what OPENINFERENCE_SPAN_KIND is set on the span

  it("maps AGENT_RUN to AGENT", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "agent",
        type: "agent_run" as any,
        startTime: new Date(),
        attributes: { agentId: "my-agent" },
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "openinference.span.kind": "AGENT",
      }),
    );
  });

  it("maps MODEL_GENERATION to LLM", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "llm-call",
        type: "model_generation" as any,
        startTime: new Date(),
        attributes: { model: "gpt-4" },
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "openinference.span.kind": "LLM",
      }),
    );
  });

  it("maps TOOL_CALL to TOOL", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "tool",
        type: "tool_call" as any,
        startTime: new Date(),
        attributes: { toolId: "search" },
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "openinference.span.kind": "TOOL",
      }),
    );
  });

  it("maps WORKFLOW_RUN to CHAIN", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "workflow",
        type: "workflow_run" as any,
        startTime: new Date(),
        attributes: {},
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "openinference.span.kind": "CHAIN",
      }),
    );
  });

  it("maps GENERIC with 'rag' in name to RETRIEVER", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "rag-search",
        type: "generic" as any,
        startTime: new Date(),
        attributes: {},
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "openinference.span.kind": "RETRIEVER",
      }),
    );
  });
});

describe("metadata extraction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets session.id from metadata", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "test",
        type: "generic" as any,
        startTime: new Date(),
        attributes: {},
        metadata: { sessionId: "sess-123" },
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "session.id": "sess-123",
      }),
    );
  });

  it("sets user.id from metadata", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "test",
        type: "generic" as any,
        startTime: new Date(),
        attributes: {},
        metadata: { userId: "user-42" },
        isEvent: false,
      } as any,
    });
    expect(mockSetAttributes).toHaveBeenCalledWith(
      expect.objectContaining({
        "user.id": "user-42",
      }),
    );
  });
});

describe("error handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sets span status to ERROR when errorInfo is present", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "failing-span",
        type: "generic" as any,
        startTime: new Date(),
        attributes: {},
        errorInfo: { message: "something went wrong" },
        isEvent: false,
      } as any,
    });
    expect(mockSetStatus).toHaveBeenCalledWith(
      expect.objectContaining({
        code: 2, // SpanStatusCode.ERROR
      }),
    );
  });

  it("sets span status to OK when no errorInfo", async () => {
    const exporter = new ArthurExporter(makeConfig());
    await exporter.exportEvent({
      type: "span_started",
      exportedSpan: {
        id: "s1",
        traceId: "t1",
        name: "ok-span",
        type: "generic" as any,
        startTime: new Date(),
        attributes: {},
        isEvent: false,
      } as any,
    });
    expect(mockSetStatus).toHaveBeenCalledWith(
      expect.objectContaining({
        code: 1, // SpanStatusCode.OK
      }),
    );
  });
});
