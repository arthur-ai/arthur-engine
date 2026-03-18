import { describe, it, expect, vi, afterEach } from "vitest";
import {
  InMemorySpanExporter,
  SimpleSpanProcessor,
} from "@opentelemetry/sdk-trace-base";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { Arthur } from "../src/arthur";

const TASK_ID = "task-uuid-0001";
const PROMPT_NAME = "TestPrompt";

const MOCK_PROMPT = {
  name: PROMPT_NAME,
  messages: [{ role: "user", content: "Hello {{ topic }}" }],
  model_name: "gpt-4o",
  model_provider: "openai",
  version: 2,
  variables: ["topic"],
  tags: ["latest"],
  config: null,
  created_at: "2025-01-01T00:00:00",
  deleted_at: null,
};

const RENDERED_PROMPT = {
  ...MOCK_PROMPT,
  messages: [{ role: "user", content: "Hello quantum computing" }],
};

function makeArthurWithInMemorySpans(taskId = TASK_ID) {
  const exporter = new InMemorySpanExporter();
  const provider = new NodeTracerProvider({
    spanProcessors: [new SimpleSpanProcessor(exporter)],
  });
  provider.register();

  const arthur = new Arthur({
    taskId,
    apiKey: "test-key",
    enableTelemetry: false,
  });
  arthur._tracerProvider = provider;
  // Mock the API client methods
  arthur._apiClient.getPromptByVersion = vi.fn();
  arthur._apiClient.getPromptByTag = vi.fn();
  arthur._apiClient.renderPrompt = vi.fn();
  arthur._apiClient.resolveTaskId = vi.fn();
  return { arthur, exporter, provider };
}

describe("getPrompt", () => {
  let provider: NodeTracerProvider;

  afterEach(async () => {
    if (provider) await provider.shutdown();
  });

  it("creates span with PROMPT kind", async () => {
    const { arthur, exporter, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByVersion).mockResolvedValue(MOCK_PROMPT);

    await arthur.getPrompt(PROMPT_NAME);

    const spans = exporter.getFinishedSpans();
    expect(spans).toHaveLength(1);
    const attrs = spans[0].attributes;
    expect(attrs["openinference.span.kind"]).toBe("PROMPT");
    expect(attrs["arthur.prompt.name"]).toBe(PROMPT_NAME);
    expect(attrs["arthur.task.id"]).toBe(TASK_ID);
    expect(attrs["llm.prompt_template.version"]).toBe("latest");
    expect(attrs["output.mime_type"]).toBe("application/json");
  });

  it("routes to tag endpoint when tag specified", async () => {
    const { arthur, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByTag).mockResolvedValue(MOCK_PROMPT);

    await arthur.getPrompt(PROMPT_NAME, { tag: "latest" });

    expect(arthur._apiClient.getPromptByTag).toHaveBeenCalledWith(
      TASK_ID,
      PROMPT_NAME,
      "latest",
    );
  });

  it("routes to version endpoint by default", async () => {
    const { arthur, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByVersion).mockResolvedValue(
      MOCK_PROMPT,
    );

    await arthur.getPrompt(PROMPT_NAME, { version: "2" });

    expect(arthur._apiClient.getPromptByVersion).toHaveBeenCalledWith(
      TASK_ID,
      PROMPT_NAME,
      "2",
    );
  });

  it("sets span status to ERROR on failure", async () => {
    const { arthur, exporter, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByVersion).mockRejectedValue(
      new Error("not found"),
    );

    await expect(arthur.getPrompt(PROMPT_NAME)).rejects.toThrow("not found");

    const spans = exporter.getFinishedSpans();
    expect(spans[0].status.code).toBe(2); // SpanStatusCode.ERROR = 2
  });
});

describe("renderPrompt", () => {
  let provider: NodeTracerProvider;

  afterEach(async () => {
    if (provider) await provider.shutdown();
  });

  it("creates span with correct attributes", async () => {
    const { arthur, exporter, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByVersion).mockResolvedValue(
      MOCK_PROMPT,
    );
    vi.mocked(arthur._apiClient.renderPrompt).mockResolvedValue(
      RENDERED_PROMPT,
    );

    await arthur.renderPrompt(PROMPT_NAME, { topic: "quantum computing" });

    const spans = exporter.getFinishedSpans();
    expect(spans).toHaveLength(1);
    const attrs = spans[0].attributes;
    expect(attrs["openinference.span.kind"]).toBe("PROMPT");
    expect(attrs["arthur.prompt.name"]).toBe(PROMPT_NAME);
  });

  it("sets template as input and rendered as output", async () => {
    const { arthur, exporter, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByVersion).mockResolvedValue(
      MOCK_PROMPT,
    );
    vi.mocked(arthur._apiClient.renderPrompt).mockResolvedValue(
      RENDERED_PROMPT,
    );

    await arthur.renderPrompt(PROMPT_NAME, { topic: "quantum computing" });

    const attrs = exporter.getFinishedSpans()[0].attributes;
    const inputVal = JSON.parse(attrs["input.value"] as string);
    expect(inputVal.messages).toEqual(MOCK_PROMPT.messages);
    expect(inputVal.variables).toEqual({ topic: "quantum computing" });

    const outputVal = JSON.parse(attrs["output.value"] as string);
    expect(outputVal.messages[0].content).toBe("Hello quantum computing");
  });

  it("sets span status to ERROR on failure", async () => {
    const { arthur, exporter, provider: p } = makeArthurWithInMemorySpans();
    provider = p;
    vi.mocked(arthur._apiClient.getPromptByVersion).mockRejectedValue(
      new Error("missing variable"),
    );

    await expect(
      arthur.renderPrompt(PROMPT_NAME, {}),
    ).rejects.toThrow("missing variable");

    expect(exporter.getFinishedSpans()[0].status.code).toBe(2);
  });
});
