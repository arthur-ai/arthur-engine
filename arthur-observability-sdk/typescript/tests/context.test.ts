import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { context } from "@opentelemetry/api";
import {
  InMemorySpanExporter,
  SimpleSpanProcessor,
} from "@opentelemetry/sdk-trace-base";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { Arthur } from "../src/arthur";

const TASK_ID = "task-uuid-ctx-test";

describe("session", () => {
  let provider: NodeTracerProvider;

  beforeEach(() => {
    // Register a real provider so context.with() actually propagates
    provider = new NodeTracerProvider();
    provider.register();
  });

  afterEach(async () => {
    await provider.shutdown();
  });

  it("runs the callback", () => {
    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    let ran = false;
    arthur.session("s1", () => {
      ran = true;
    });
    expect(ran).toBe(true);
  });

  it("sets session.id in context during callback", () => {
    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    let sessionId: any;
    arthur.session("session-abc", () => {
      sessionId = context.active().getValue(Symbol.for("session.id"));
    });
    expect(sessionId).toBe("session-abc");
  });

  it("works with async callbacks", async () => {
    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    const result = await arthur.session("s1", async () => {
      return "hello";
    });
    expect(result).toBe("hello");
  });
});

describe("user", () => {
  let provider: NodeTracerProvider;

  beforeEach(() => {
    provider = new NodeTracerProvider();
    provider.register();
  });

  afterEach(async () => {
    await provider.shutdown();
  });

  it("runs the callback", () => {
    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    let ran = false;
    arthur.user("u1", () => {
      ran = true;
    });
    expect(ran).toBe(true);
  });

  it("sets user.id in context during callback", () => {
    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    let userId: any;
    arthur.user("user-42", () => {
      userId = context.active().getValue(Symbol.for("user.id"));
    });
    expect(userId).toBe("user-42");
  });
});

describe("attributes", () => {
  let provider: NodeTracerProvider;

  beforeEach(() => {
    provider = new NodeTracerProvider();
    provider.register();
  });

  afterEach(async () => {
    await provider.shutdown();
  });

  it("sets combined attributes in context", () => {
    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    let sessionId: any;
    let userId: any;
    arthur.attributes(
      { sessionId: "attr-session", userId: "attr-user" },
      () => {
        sessionId = context.active().getValue(Symbol.for("session.id"));
        userId = context.active().getValue(Symbol.for("user.id"));
      },
    );
    expect(sessionId).toBe("attr-session");
    expect(userId).toBe("attr-user");
  });
});

describe("prompt span context propagation", () => {
  let provider: NodeTracerProvider;

  afterEach(async () => {
    if (provider) await provider.shutdown();
  });

  it("get_prompt span includes session.id from context", async () => {
    const exporter = new InMemorySpanExporter();
    provider = new NodeTracerProvider({
      spanProcessors: [new SimpleSpanProcessor(exporter)],
    });
    provider.register();

    const arthur = new Arthur({
      taskId: TASK_ID,
      apiKey: "test-key",
      enableTelemetry: false,
    });
    arthur._tracerProvider = provider;
    arthur._apiClient.getPromptByVersion = vi.fn().mockResolvedValue({
      name: "TestPrompt",
      messages: [],
      variables: [],
    });

    await arthur.session("span-session", async () => {
      await arthur.getPrompt("TestPrompt");
    });

    const attrs = exporter.getFinishedSpans()[0].attributes;
    expect(attrs["session.id"]).toBe("span-session");
  });
});
