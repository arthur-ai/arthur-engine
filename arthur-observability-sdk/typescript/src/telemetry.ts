import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
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

  // Note: we intentionally do NOT call provider.register() here.
  // The provider is passed explicitly to instrumentors and used directly
  // by Arthur._getTracer(). Registering globally would silently replace
  // any existing OTel provider the user may have configured.

  return provider;
}
