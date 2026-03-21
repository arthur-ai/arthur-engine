# Getting Started with the Arthur Observability SDK (TypeScript)

This guide walks through installing and wiring up the Arthur Observability SDK in a
Node.js/TypeScript application.  After following these steps you will have traces and spans
flowing to your Arthur GenAI Engine instance.

---

## Installation

```bash
npm install @arthur-ai/observability-sdk
```

To enable instrumentation for a specific framework install the matching package:

```bash
npm install @arizeai/openinference-instrumentation-openai      # OpenAI
npm install @arizeai/openinference-instrumentation-langchain   # LangChain
npm install @arizeai/openinference-instrumentation-anthropic   # Anthropic
```

---

## Initialising Arthur

Create a single `Arthur` instance at application startup.  At least one of `taskId`,
`taskName`, or `serviceName` must be provided.

```typescript
import { Arthur } from "@arthur-ai/observability-sdk";

const arthur = new Arthur({
  apiKey: "your-api-key",        // or set ARTHUR_API_KEY env var
  taskId: "<uuid>",              // Arthur task UUID
  // taskName: "my-chatbot",     // alternative: resolved lazily to a UUID
  // serviceName: "my-service",  // OTel service.name resource attribute
  enableTelemetry: true,         // default true; set false to skip OTel setup
});
```

### Constructor options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `apiKey` | `string` | `ARTHUR_API_KEY` env var | **Required.** Arthur API key. Throws if neither the option nor the env var is set. |
| `baseUrl` | `string` | `ARTHUR_BASE_URL` or `http://localhost:3030` | Base URL of the Arthur GenAI Engine. |
| `taskId` | `string` | — | Arthur task UUID. Used for prompt fetching. |
| `taskName` | `string` | — | Task name — resolved lazily to a UUID via the API on the first prompt call. |
| `serviceName` | `string` | — | OTel `service.name` resource attribute. |
| `resourceAttributes` | `Record<string, string>` | `{}` | Additional OTel resource attributes merged into the `TracerProvider`. |
| `enableTelemetry` | `boolean` | `true` | When `false`, no `TracerProvider` is created (useful for prompt-only usage). |
| `otlpEndpoint` | `string` | `{baseUrl}/api/v1/traces` | OTLP HTTP traces endpoint. |

When `enableTelemetry` is `true` a `BatchSpanProcessor` backed by an OTLP HTTP exporter is
configured.  The `apiKey` is sent as an `Authorization: Bearer` header on every OTLP request.
The provider is **not** registered globally — it is passed explicitly to instrumentors to
avoid replacing any existing OTel provider.

---

## Session context

Tag all spans created within a callback with a `session.id` attribute — useful for grouping
all traces from a single conversation or request chain.

```typescript
await arthur.session("session-abc-123", async () => {
  const response = await openai.chat.completions.create(...);
});
```

---

## User context

Tag all spans with a `user.id` attribute.

```typescript
await arthur.user("user-42", async () => {
  const response = await openai.chat.completions.create(...);
});
```

---

## Combined session and user context

Use `arthur.attributes()` to set multiple OpenInference attributes at once.

```typescript
await arthur.attributes(
  { sessionId: "session-abc-123", userId: "user-42", tags: ["prod"] },
  async () => {
    const response = await openai.chat.completions.create(...);
  },
);
```

`arthur.attributes()` accepts `sessionId`, `userId`, `metadata`, and `tags`.

---

## Wiring a framework

Call the relevant `instrument*` method **once** after constructing `Arthur`.  The
instrumentor patches the framework's HTTP client so that every call is automatically
recorded as an OTel span.

```typescript
// OpenAI (requires: npm install @arizeai/openinference-instrumentation-openai)
arthur.instrumentOpenAI();

// LangChain (requires: npm install @arizeai/openinference-instrumentation-langchain)
arthur.instrumentLangchain();

// Anthropic (requires: npm install @arizeai/openinference-instrumentation-anthropic)
arthur.instrumentAnthropic();
```

### Supported instrumentors

| Method | npm Package |
|--------|-------------|
| `instrumentOpenAI()` | `@arizeai/openinference-instrumentation-openai` |
| `instrumentAnthropic()` | `@arizeai/openinference-instrumentation-anthropic` |
| `instrumentLangchain()` | `@arizeai/openinference-instrumentation-langchain` |
| `instrumentClaudeAgentSdk()` | `@arizeai/openinference-instrumentation-claude-agent-sdk` |
| `instrumentBedrock()` | `@arizeai/openinference-instrumentation-bedrock` |
| `instrumentBedrockAgent()` | `@arizeai/openinference-instrumentation-bedrock-agent-runtime` |
| `instrumentBeeAI()` | `@arizeai/openinference-instrumentation-beeai` |
| `instrumentMCP()` | `@arizeai/openinference-instrumentation-mcp` |

If the optional package is not installed the method throws with an `npm install` hint.

---

## Mastra integration

For [Mastra](https://mastra.ai) applications, use the dedicated `ArthurExporter` which
implements Mastra's `AITracingExporter` interface.  Import it from the `./mastra` subpath
export.

### Option 1: Create from an Arthur instance

```typescript
import { Arthur } from "@arthur-ai/observability-sdk";
import { Mastra } from "@mastra/core";

const arthur = new Arthur({
  apiKey: "your-api-key",
  taskId: "<your-task-uuid>",
  serviceName: "my-agent",
});

const exporter = arthur.createMastraExporter();

const mastra = new Mastra({
  agents: { /* ... */ },
  observability: {
    configs: {
      arthur: {
        serviceName: "my-agent",
        exporters: [exporter],
      },
    },
  },
});
```

### Option 2: Create directly

```typescript
import { ArthurExporter } from "@arthur-ai/observability-sdk/mastra";
import { Mastra } from "@mastra/core";

const exporter = new ArthurExporter({
  url: "https://app.arthur.ai",
  apiKey: "your-api-key",
  taskId: "<your-task-uuid>",
  serviceName: "my-agent",
});

const mastra = new Mastra({
  agents: { /* ... */ },
  observability: {
    configs: {
      arthur: {
        serviceName: "my-agent",
        exporters: [exporter],
      },
    },
  },
});
```

The `ArthurExporter` creates its own standalone `NodeTracerProvider` and manages span
lifecycle internally.  It handles all 13 Mastra span types and maps them to OpenInference
semantic conventions.

Requires `@mastra/core` as an optional peer dependency:

```bash
npm install @mastra/core
```

---

## Shutdown

Call `arthur.shutdown()` before your process exits to flush all pending spans:

```typescript
await arthur.shutdown();
```

`shutdown()` calls `TracerProvider.forceFlush()` and `TracerProvider.shutdown()`, then
closes the underlying API client connection pool.

---

## Minimal end-to-end example

```typescript
import { Arthur } from "@arthur-ai/observability-sdk";
import OpenAI from "openai";

const arthur = new Arthur({
  apiKey: "your-api-key",
  taskId: "<your-task-uuid>",
  serviceName: "my-chatbot",
});
arthur.instrumentOpenAI();

const client = new OpenAI();

await arthur.attributes(
  { sessionId: "sess-1", userId: "user-99" },
  async () => {
    const response = await client.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: "Hello!" }],
    });
    console.log(response.choices[0].message.content);
  },
);

await arthur.shutdown();
```
