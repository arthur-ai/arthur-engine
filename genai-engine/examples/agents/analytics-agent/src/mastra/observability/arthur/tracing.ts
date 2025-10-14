/**
 * Arthur Exporter for Mastra AI Tracing
 *
 * This exporter sends tracing data to Arthur using OpenInference semantic format
 * via OpenTelemetry OTLP protocol. It converts Mastra AI tracing events to
 * OpenTelemetry spans with OpenInference attributes.
 */

import type {
  AITracingExporter,
  AITracingEvent,
  AnyExportedAISpan,
} from "@mastra/core/ai-tracing";
import { ConsoleLogger } from "@mastra/core/logger";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-proto";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { trace, Context, SpanKind, ROOT_CONTEXT } from "@opentelemetry/api";
import { resourceFromAttributes } from "@opentelemetry/resources";
import {
  OITracer,
  OISpan,
  TraceConfigOptions,
} from "@arizeai/openinference-core";
import { setSpanAttributes, setSpanErrorInfo } from "./attribute-utils";

export interface ArthurExporterConfig {
  url: string;
  headers: Record<string, string>;
  taskId: string;
  serviceName: string;

  traceConfig?: TraceConfigOptions;

  /** Logger level for diagnostic messages (default: 'warn') */
  logLevel?: "debug" | "info" | "warn" | "error";
}

export class ArthurExporter implements AITracingExporter {
  name = "arthur";
  private logger: ConsoleLogger;
  private provider: NodeTracerProvider;
  private tracer: OITracer;
  private taskId: string;
  private spanMap = new Map<string, OISpan>();
  private serviceName: string;

  constructor(config: ArthurExporterConfig) {
    this.logger = new ConsoleLogger({ level: config.logLevel ?? "warn" });
    this.taskId = config.taskId;
    this.serviceName = config.serviceName;

    // Ensure URL ends with '/v1/traces' regardless of trailing slash
    const baseUrl = config.url.endsWith("/")
      ? config.url.slice(0, -1)
      : config.url;
    const tracesUrl = `${baseUrl}/v1/traces`;

    const exporter = new OTLPTraceExporter({
      url: tracesUrl,
      headers: config.headers,
    });

    // Create a standalone provider (not registered globally)
    this.provider = new NodeTracerProvider({
      resource: resourceFromAttributes({
        "service.name": this.serviceName,
        "arthur.task": this.taskId,
      }),
      spanProcessors: [new BatchSpanProcessor(exporter)],
    });

    // Important: no provider.register() call!
    // We create an OITracer from our private provider
    const otelTracer = this.provider.getTracer(
      "@mastra/arthur-exporter",
      "1.0.0"
    );
    this.tracer = new OITracer({
      tracer: otelTracer,
      traceConfig: config.traceConfig,
    });
  }

  async exportEvent(event: AITracingEvent): Promise<void> {
    try {
      if (event.exportedSpan.isEvent) {
        await this.handleEventSpan(event.exportedSpan);
        return;
      }

      switch (event.type) {
        case "span_started":
          await this.handleSpanStarted(event.exportedSpan);
          break;
        case "span_updated":
          await this.handleSpanUpdate(event.exportedSpan);
          break;
        case "span_ended":
          await this.handleSpanEnded(event.exportedSpan);
          break;
      }
    } catch (error) {
      this.logger.error("Arthur exporter: Error processing event", {
        error: error instanceof Error ? error.message : String(error),
        eventType: event.type,
        spanId: event.exportedSpan.id,
        traceId: event.exportedSpan.traceId,
      });
    }
  }

  private async handleSpanStarted(span: AnyExportedAISpan): Promise<void> {
    const otelSpan = this.createOtelSpan(span);
    this.spanMap.set(span.id, otelSpan);
  }

  private async handleSpanUpdate(span: AnyExportedAISpan): Promise<void> {
    const existingSpan = this.spanMap.get(span.id);
    if (existingSpan) {
      this.updateOtelSpan(existingSpan, span);
    }
  }

  private async handleSpanEnded(span: AnyExportedAISpan): Promise<void> {
    const existingSpan = this.spanMap.get(span.id);
    if (existingSpan) {
      this.updateOtelSpan(existingSpan, span);
      existingSpan.end(span.endTime);
      this.spanMap.delete(span.id);
    }
  }

  private async handleEventSpan(span: AnyExportedAISpan): Promise<void> {
    const otelSpan = this.createOtelSpan(span);
    this.updateOtelSpan(otelSpan, span);
    // Event spans end immediately for events
    otelSpan.end();
  }

  private createOtelSpan(span: AnyExportedAISpan): OISpan {
    // Create parent context if parent exists
    // Use root context so we don't pick up any parent
    // spans set from other exporters in the current thread context
    let parentCtx: Context = ROOT_CONTEXT;
    if (span.parentSpanId) {
      const parentSpan = this.spanMap.get(span.parentSpanId);
      if (parentSpan) {
        parentCtx = trace.setSpan(ROOT_CONTEXT, parentSpan);
      }
    }

    // Create span with proper timing
    const otelSpan = this.tracer.startSpan(
      span.name,
      {
        startTime: span.startTime,
        kind: SpanKind.INTERNAL,
      },
      parentCtx
    );

    // Set all attributes and error info
    this.updateOtelSpan(otelSpan, span);

    return otelSpan;
  }

  private updateOtelSpan(otelSpan: OISpan, span: AnyExportedAISpan): void {
    setSpanAttributes(otelSpan, span);
    setSpanErrorInfo(otelSpan, span.errorInfo);
  }

  async shutdown(): Promise<void> {
    try {
      // End any remaining spans
      for (const span of this.spanMap.values()) {
        span.end();
      }
      this.spanMap.clear();

      // Shutdown the provider
      await this.provider.shutdown();

      this.logger.info("Arthur exporter: Shutdown completed");
    } catch (error) {
      this.logger.error("Arthur exporter: Error during shutdown", {
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }
}
