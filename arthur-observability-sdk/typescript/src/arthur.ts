import {
  context,
  trace,
  Span,
  SpanStatusCode,
  Tracer,
} from "@opentelemetry/api";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { ArthurAPIClient } from "./client";
import { setupTelemetry } from "./telemetry";

export interface ArthurOptions {
  apiKey?: string;
  baseUrl?: string;
  serviceName?: string;
  resourceAttributes?: Record<string, string>;
  taskId?: string;
  taskName?: string;
  enableTelemetry?: boolean;
  otlpEndpoint?: string;
}

export interface GetPromptOptions {
  version?: string;
  tag?: string;
  taskId?: string;
}

export interface RenderPromptOptions {
  version?: string;
  tag?: string;
  strict?: boolean;
  taskId?: string;
}

export interface AttributeOptions {
  sessionId?: string;
  userId?: string;
  metadata?: Record<string, string>;
  tags?: string[];
}

export class Arthur {
  private readonly _apiKey: string;
  private readonly _baseUrl: string;
  private readonly _serviceName?: string;
  private readonly _resourceAttributes: Record<string, string>;
  private readonly _taskId?: string;
  private readonly _taskName?: string;
  private readonly _enableTelemetry: boolean;
  private readonly _otlpEndpoint: string;
  // Exposed for testing
  _tracerProvider: NodeTracerProvider | null = null;
  _apiClient: ArthurAPIClient;
  private _resolvedTaskId?: string;

  constructor(options: ArthurOptions = {}) {
    const apiKey = options.apiKey ?? process.env.ARTHUR_API_KEY;
    if (!apiKey) {
      throw new Error(
        "Arthur requires an API key. Provide apiKey or set the ARTHUR_API_KEY environment variable.",
      );
    }
    this._apiKey = apiKey;

    this._baseUrl = (
      options.baseUrl ??
      process.env.ARTHUR_BASE_URL ??
      "http://localhost:3030"
    ).replace(/\/+$/, "");

    this._serviceName = options.serviceName;
    this._resourceAttributes = options.resourceAttributes ?? {};
    this._taskId = options.taskId;
    this._taskName = options.taskName;
    this._enableTelemetry = options.enableTelemetry ?? true;
    this._otlpEndpoint =
      options.otlpEndpoint ?? `${this._baseUrl}/api/v1/traces`;

    if (!options.taskId && !options.taskName && !options.serviceName) {
      throw new Error(
        "Arthur requires at least one of: taskId, taskName, or serviceName. " +
          "Provide a task context for prompt fetching or a serviceName for telemetry.",
      );
    }

    if (this._enableTelemetry) {
      const effectiveServiceName =
        this._serviceName ?? this._taskName ?? this._taskId ?? "arthur-app";
      this._tracerProvider = setupTelemetry({
        serviceName: effectiveServiceName,
        otlpEndpoint: this._otlpEndpoint,
        apiKey: this._apiKey,
        resourceAttributes: this._resourceAttributes,
      });
    }

    this._apiClient = new ArthurAPIClient(this._baseUrl, this._apiKey);
    this._resolvedTaskId = options.taskId;
  }

  // --- Public properties ---

  get taskId(): string | undefined {
    return this._resolvedTaskId;
  }

  get taskName(): string | undefined {
    return this._taskName;
  }

  get telemetryActive(): boolean {
    return this._tracerProvider !== null;
  }

  // --- Internal helpers ---

  private async _getTaskId(override?: string): Promise<string> {
    if (override) return override;
    if (this._resolvedTaskId) return this._resolvedTaskId;
    if (this._taskName) {
      this._resolvedTaskId = await this._apiClient.resolveTaskId(
        this._taskName,
      );
      return this._resolvedTaskId;
    }
    throw new Error(
      "No task_id available. Provide taskId or taskName when initialising Arthur.",
    );
  }

  private _getTracer(): Tracer {
    const provider = this._tracerProvider ?? trace.getTracerProvider();
    return provider.getTracer("openinference.instrumentation.arthur");
  }

  private _applyOpenInferenceContext(span: Span): void {
    // Read OpenInference context attributes and apply to span
    const keys = ["session.id", "user.id", "metadata", "tag.tags"];
    for (const key of keys) {
      const value = context.active().getValue(Symbol.for(key));
      if (value !== undefined && value !== null) {
        span.setAttribute(key, value as string | string[]);
      }
    }
  }

  // --- Prompt management ---

  async getPrompt(
    name: string,
    options: GetPromptOptions = {},
  ): Promise<Record<string, any>> {
    const { version = "latest", tag, taskId } = options;
    const resolvedTaskId = await this._getTaskId(taskId);
    const tracer = this._getTracer();

    return tracer.startActiveSpan("get_prompt", async (span) => {
      span.setAttribute("openinference.span.kind", "PROMPT");
      span.setAttribute("arthur.prompt.name", name);
      span.setAttribute("arthur.task.id", resolvedTaskId);
      this._applyOpenInferenceContext(span);

      const resolvedVersion = tag ?? version;
      span.setAttribute("llm.prompt_template.version", resolvedVersion);

      try {
        let promptData: Record<string, any>;
        if (tag) {
          promptData = await this._apiClient.getPromptByTag(
            resolvedTaskId,
            name,
            tag,
          );
        } else {
          promptData = await this._apiClient.getPromptByVersion(
            resolvedTaskId,
            name,
            version,
          );
        }

        const messages = promptData.messages ?? [];
        span.setAttribute(
          "llm.prompt_template.template",
          JSON.stringify(messages),
        );
        span.setAttribute(
          "llm.prompt_template.variables",
          JSON.stringify(promptData.variables ?? []),
        );
        span.setAttribute("output.value", JSON.stringify(promptData));
        span.setAttribute("output.mime_type", "application/json");

        span.end();
        return promptData;
      } catch (err) {
        span.recordException(err as Error);
        span.setStatus({ code: SpanStatusCode.ERROR, message: String(err) });
        span.end();
        throw err;
      }
    });
  }

  async renderPrompt(
    name: string,
    variables: Record<string, string>,
    options: RenderPromptOptions = {},
  ): Promise<Record<string, any>> {
    const { version = "latest", tag, strict = false, taskId } = options;
    const resolvedTaskId = await this._getTaskId(taskId);
    const effectiveVersion = tag ?? version;
    const tracer = this._getTracer();

    return tracer.startActiveSpan("render_prompt", async (span) => {
      span.setAttribute("openinference.span.kind", "PROMPT");
      span.setAttribute("arthur.prompt.name", name);
      span.setAttribute("arthur.task.id", resolvedTaskId);
      span.setAttribute("llm.prompt_template.version", effectiveVersion);
      this._applyOpenInferenceContext(span);

      try {
        // Fetch original template
        let templateData: Record<string, any>;
        if (tag) {
          templateData = await this._apiClient.getPromptByTag(
            resolvedTaskId,
            name,
            tag,
          );
        } else {
          templateData = await this._apiClient.getPromptByVersion(
            resolvedTaskId,
            name,
            version,
          );
        }

        // Render
        const promptData = await this._apiClient.renderPrompt(
          resolvedTaskId,
          name,
          effectiveVersion,
          variables,
          strict,
        );

        // INPUT: original template messages + variable values
        const templateMessages = templateData.messages ?? [];
        span.setAttribute(
          "llm.prompt_template.template",
          JSON.stringify(templateMessages),
        );
        span.setAttribute(
          "llm.prompt_template.variables",
          JSON.stringify(variables),
        );
        span.setAttribute(
          "input.value",
          JSON.stringify({ messages: templateMessages, variables }),
        );
        span.setAttribute("input.mime_type", "application/json");

        // OUTPUT: rendered result
        span.setAttribute("output.value", JSON.stringify(promptData));
        span.setAttribute("output.mime_type", "application/json");

        span.end();
        return promptData;
      } catch (err) {
        span.recordException(err as Error);
        span.setStatus({ code: SpanStatusCode.ERROR, message: String(err) });
        span.end();
        throw err;
      }
    });
  }

  // --- Session / user context helpers ---

  session<T>(sessionId: string, fn: () => T | Promise<T>): T | Promise<T> {
    const ctx = context.active().setValue(Symbol.for("session.id"), sessionId);
    return context.with(ctx, fn);
  }

  user<T>(userId: string, fn: () => T | Promise<T>): T | Promise<T> {
    const ctx = context.active().setValue(Symbol.for("user.id"), userId);
    return context.with(ctx, fn);
  }

  attributes<T>(
    attrs: AttributeOptions,
    fn: () => T | Promise<T>,
  ): T | Promise<T> {
    let ctx = context.active();
    if (attrs.sessionId) {
      ctx = ctx.setValue(Symbol.for("session.id"), attrs.sessionId);
    }
    if (attrs.userId) {
      ctx = ctx.setValue(Symbol.for("user.id"), attrs.userId);
    }
    if (attrs.metadata) {
      ctx = ctx.setValue(
        Symbol.for("metadata"),
        JSON.stringify(attrs.metadata),
      );
    }
    if (attrs.tags) {
      ctx = ctx.setValue(Symbol.for("tag.tags"), attrs.tags);
    }
    return context.with(ctx, fn);
  }

  // --- Instrumentors ---

  private _instrument(
    packageName: string,
    extrasKey: string,
    className: string,
    targetModuleName?: string,
  ): any {
    let mod: any;
    try {
      mod = require(packageName);
    } catch {
      throw new Error(
        `Missing optional dependency '${packageName}'. ` +
          `Install it with: npm install ${packageName}`,
      );
    }
    const InstrumentorClass = mod[className];
    if (!InstrumentorClass) {
      throw new Error(
        `Module '${packageName}' does not export '${className}'. ` +
          `You may have an incompatible version of '${packageName}'.`,
      );
    }
    const instrumentor = new InstrumentorClass();
    if (
      this._tracerProvider &&
      typeof instrumentor.setTracerProvider === "function"
    ) {
      instrumentor.setTracerProvider(this._tracerProvider);
    }
    if (
      typeof instrumentor.manuallyInstrument === "function" &&
      targetModuleName
    ) {
      const targetModule = require(targetModuleName);
      instrumentor.manuallyInstrument(targetModule);
    } else if (typeof instrumentor.manuallyInstrument === "function") {
      instrumentor.manuallyInstrument();
    } else {
      const opts: any = {};
      if (this._tracerProvider) {
        opts.tracerProvider = this._tracerProvider;
      }
      instrumentor.instrument(opts);
    }
    return instrumentor;
  }

  instrumentOpenAI(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-openai",
      "openai",
      "OpenAIInstrumentation",
      "openai",
    );
  }

  instrumentAnthropic(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-anthropic",
      "anthropic",
      "AnthropicInstrumentation",
      "@anthropic-ai/sdk",
    );
  }

  instrumentLangchain(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-langchain",
      "langchain",
      "LangChainInstrumentation",
    );
  }

  instrumentClaudeAgentSdk(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-claude-agent-sdk",
      "claude-agent-sdk",
      "ClaudeAgentSDKInstrumentation",
      "@anthropic-ai/claude-agent-sdk",
    );
  }

  instrumentBedrock(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-bedrock",
      "bedrock",
      "BedrockInstrumentation",
      "@aws-sdk/client-bedrock-runtime",
    );
  }

  instrumentBedrockAgent(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-bedrock-agent-runtime",
      "bedrock-agent-runtime",
      "BedrockAgentInstrumentation",
      "@aws-sdk/client-bedrock-agent-runtime",
    );
  }

  instrumentBeeAI(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-beeai",
      "beeai",
      "BeeAIInstrumentation",
    );
  }

  instrumentMCP(): any {
    return this._instrument(
      "@arizeai/openinference-instrumentation-mcp",
      "mcp",
      "MCPInstrumentation",
      "@modelcontextprotocol/sdk",
    );
  }

  // --- Mastra ---

  createMastraExporter(overrides?: Record<string, any>): any {
    const taskId = overrides?.taskId ?? this._resolvedTaskId ?? this._taskId;
    if (!taskId) {
      throw new Error(
        "Cannot create Mastra exporter: taskId is unavailable. " +
          "Provide taskId directly, pass it via overrides, or call getPrompt/renderPrompt first to resolve taskName.",
      );
    }
    const { ArthurExporter } = require("./mastra");
    return new ArthurExporter({
      url: this._baseUrl,
      apiKey: this._apiKey,
      taskId,
      serviceName: this._serviceName ?? "arthur-app",
      ...overrides,
    });
  }

  // --- Shutdown ---

  async shutdown(_timeoutMillis: number = 30_000): Promise<void> {
    try {
      if (this._tracerProvider) {
        await this._tracerProvider.forceFlush().catch(() => {});
        await this._tracerProvider.shutdown().catch(() => {});
      }
    } finally {
      this._apiClient.close();
    }
  }
}
