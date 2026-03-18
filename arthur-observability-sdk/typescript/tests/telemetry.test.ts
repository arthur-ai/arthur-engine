import { describe, it, expect, vi, beforeEach } from "vitest";

const { mockRegister, mockBatchSpanProcessor, mockExporter, mockResource } =
  vi.hoisted(() => ({
    mockRegister: vi.fn(),
    mockBatchSpanProcessor: vi.fn(),
    mockExporter: vi.fn(),
    mockResource: vi
      .fn()
      .mockImplementation((attrs: any) => ({ attributes: attrs })),
  }));

vi.mock("@opentelemetry/sdk-trace-node", () => ({
  NodeTracerProvider: vi.fn().mockImplementation(() => ({
    register: mockRegister,
    getTracer: vi.fn(),
    forceFlush: vi.fn(() => Promise.resolve()),
    shutdown: vi.fn(() => Promise.resolve()),
  })),
}));

vi.mock("@opentelemetry/sdk-trace-base", () => ({
  BatchSpanProcessor: mockBatchSpanProcessor,
}));

vi.mock("@opentelemetry/exporter-trace-otlp-http", () => ({
  OTLPTraceExporter: mockExporter,
}));

vi.mock("@opentelemetry/resources", () => ({
  Resource: mockResource,
}));

vi.mock("@opentelemetry/semantic-conventions", () => ({
  ATTR_SERVICE_NAME: "service.name",
}));

import { setupTelemetry } from "../src/telemetry";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";

describe("setupTelemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns a NodeTracerProvider", () => {
    const provider = setupTelemetry({
      serviceName: "test-service",
      otlpEndpoint: "http://localhost:4318/v1/traces",
      apiKey: "test-key",
    });
    expect(provider).toBeDefined();
    expect(NodeTracerProvider).toHaveBeenCalled();
  });

  it("always passes auth header to exporter", () => {
    setupTelemetry({
      serviceName: "test-service",
      otlpEndpoint: "http://localhost:4318/v1/traces",
      apiKey: "my-secret-key",
    });
    expect(mockExporter).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer my-secret-key",
        }),
      }),
    );
  });

  it("sends auth header even for non-HTTPS endpoints", () => {
    setupTelemetry({
      serviceName: "svc",
      otlpEndpoint: "http://plain-http:4318/v1/traces",
      apiKey: "key",
    });
    expect(mockExporter).toHaveBeenCalledWith(
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer key",
        }),
      }),
    );
  });

  it("merges custom resource attributes", () => {
    setupTelemetry({
      serviceName: "test-service",
      otlpEndpoint: "http://localhost:4318/v1/traces",
      apiKey: "key",
      resourceAttributes: { "deployment.environment": "staging", team: "ml" },
    });
    expect(mockResource).toHaveBeenCalledWith(
      expect.objectContaining({
        "service.name": "test-service",
        "deployment.environment": "staging",
        team: "ml",
      }),
    );
  });

  it("does not register the provider globally", () => {
    setupTelemetry({
      serviceName: "svc",
      otlpEndpoint: "http://localhost:4318/v1/traces",
      apiKey: "key",
    });
    expect(mockRegister).not.toHaveBeenCalled();
  });
});
