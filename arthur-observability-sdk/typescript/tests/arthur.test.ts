import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We need to mock telemetry before importing Arthur
vi.mock("../src/telemetry", () => ({
  setupTelemetry: vi.fn(() => ({
    getTracer: vi.fn(() => ({
      startActiveSpan: vi.fn(),
    })),
    forceFlush: vi.fn(() => Promise.resolve()),
    shutdown: vi.fn(() => Promise.resolve()),
    register: vi.fn(),
  })),
}));

import { Arthur } from "../src/arthur";

describe("Arthur constructor", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
    delete process.env.ARTHUR_API_KEY;
    delete process.env.ARTHUR_BASE_URL;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("requires api_key (param or env var)", () => {
    expect(() => new Arthur({ serviceName: "svc" })).toThrow(
      "Arthur requires an API key",
    );
  });

  it("requires at least one of taskId, taskName, serviceName", () => {
    expect(() => new Arthur({ apiKey: "test-key" })).toThrow(
      "Arthur requires at least one of",
    );
  });

  it("accepts taskId only", () => {
    const a = new Arthur({
      taskId: "uuid-1234",
      apiKey: "test-key",
      enableTelemetry: false,
    });
    expect(a.taskId).toBe("uuid-1234");
  });

  it("accepts taskName only", () => {
    const a = new Arthur({
      taskName: "my-task",
      apiKey: "test-key",
      enableTelemetry: false,
    });
    expect(a.taskName).toBe("my-task");
  });

  it("accepts serviceName only", () => {
    const a = new Arthur({
      serviceName: "my-svc",
      apiKey: "test-key",
      enableTelemetry: false,
    });
    expect(a.telemetryActive).toBe(false);
  });

  it("reads apiKey from env var", () => {
    process.env.ARTHUR_API_KEY = "env-api-key";
    const a = new Arthur({ serviceName: "svc", enableTelemetry: false });
    expect((a as any)._apiKey).toBe("env-api-key");
  });

  it("param apiKey overrides env var", () => {
    process.env.ARTHUR_API_KEY = "env-api-key";
    const a = new Arthur({
      apiKey: "param-key",
      serviceName: "svc",
      enableTelemetry: false,
    });
    expect((a as any)._apiKey).toBe("param-key");
  });

  it("reads baseUrl from env var", () => {
    process.env.ARTHUR_BASE_URL = "http://custom:9090";
    const a = new Arthur({
      serviceName: "svc",
      apiKey: "k",
      enableTelemetry: false,
    });
    expect((a as any)._baseUrl).toBe("http://custom:9090");
  });

  it("param baseUrl overrides env var", () => {
    process.env.ARTHUR_BASE_URL = "http://env:9090";
    const a = new Arthur({
      serviceName: "svc",
      apiKey: "k",
      baseUrl: "http://explicit:8080",
      enableTelemetry: false,
    });
    expect((a as any)._baseUrl).toBe("http://explicit:8080");
  });

  it("defaults baseUrl to localhost:3030", () => {
    const a = new Arthur({
      serviceName: "svc",
      apiKey: "k",
      enableTelemetry: false,
    });
    expect((a as any)._baseUrl).toBe("http://localhost:3030");
  });

  it("defaults otlpEndpoint to {baseUrl}/api/v1/traces", () => {
    const a = new Arthur({
      serviceName: "svc",
      apiKey: "k",
      baseUrl: "http://my-host:3030",
      enableTelemetry: false,
    });
    expect((a as any)._otlpEndpoint).toBe("http://my-host:3030/api/v1/traces");
  });

  it("enableTelemetry=false skips provider creation", () => {
    const a = new Arthur({
      serviceName: "svc",
      apiKey: "k",
      enableTelemetry: false,
    });
    expect(a.telemetryActive).toBe(false);
    expect((a as any)._tracerProvider).toBeNull();
  });
});
