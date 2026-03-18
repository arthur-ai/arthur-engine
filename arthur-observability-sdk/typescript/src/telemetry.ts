import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { Resource } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";

export interface TelemetryOptions {
  serviceName: string;
  otlpEndpoint: string;
  apiKey: string;
  resourceAttributes?: Record<string, string>;
}

export function setupTelemetry(options: TelemetryOptions): NodeTracerProvider {
  const { serviceName, otlpEndpoint, apiKey, resourceAttributes } = options;

  const attrs: Record<string, string> = {
    [ATTR_SERVICE_NAME]: serviceName,
    ...resourceAttributes,
  };

  const resource = new Resource(attrs);

  const headers: Record<string, string> = {};
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const exporter = new OTLPTraceExporter({
    url: otlpEndpoint,
    headers,
  });

  const provider = new NodeTracerProvider({
    resource,
    spanProcessors: [new BatchSpanProcessor(exporter)],
  });

  // Register globally so that instrumentors (which create spans via
  // trace.getTracer()) use this provider instead of the NoopTracerProvider.
  provider.register();

  return provider;
}
