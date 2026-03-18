# Arthur Observability SDK (TypeScript)

TypeScript/Node.js SDK for Arthur AI observability — telemetry, prompt management, and framework instrumentation via OpenTelemetry and OpenInference conventions.

## Installation

```bash
npm install @arthur-ai/observability-sdk
```

## Quick Start

```typescript
import { Arthur } from "@arthur-ai/observability-sdk";

const arthur = new Arthur({
  apiKey: "your-api-key", // or set ARTHUR_API_KEY env var
  taskId: "<your-task-uuid>",
  serviceName: "my-chatbot",
});

// Instrument OpenAI (optional — install @arizeai/openinference-instrumentation-openai)
arthur.instrumentOpenAI();

import OpenAI from "openai";
const client = new OpenAI();

await arthur.session("sess-1", async () => {
  // Fetch and render a prompt template
  const rendered = await arthur.renderPrompt("rag-answer", {
    context: "...",
    question: "What is quantum computing?",
  });

  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: rendered.messages,
  });
  console.log(response.choices[0].message.content);
});

await arthur.shutdown();
```

## Constructor Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `apiKey` | `string` | `ARTHUR_API_KEY` env var | **Required.** Arthur API key. |
| `baseUrl` | `string` | `ARTHUR_BASE_URL` or `http://localhost:3030` | Arthur GenAI Engine base URL. |
| `taskId` | `string` | — | Arthur task UUID for prompt fetching. |
| `taskName` | `string` | — | Task name (resolved lazily to UUID via API). |
| `serviceName` | `string` | — | OTel `service.name` resource attribute. |
| `enableTelemetry` | `boolean` | `true` | Set `false` to skip TracerProvider creation. |
| `otlpEndpoint` | `string` | `{baseUrl}/api/v1/traces` | OTLP HTTP traces endpoint. |
| `resourceAttributes` | `Record<string, string>` | `{}` | Additional OTel resource attributes. |

At least one of `taskId`, `taskName`, or `serviceName` must be provided.

## Prompt Management

```typescript
// Fetch a prompt by version (default: "latest")
const prompt = await arthur.getPrompt("my-prompt", { version: "2" });

// Fetch by tag
const prompt = await arthur.getPrompt("my-prompt", { tag: "production" });

// Render a prompt with variable substitution
const rendered = await arthur.renderPrompt("my-prompt", {
  topic: "quantum computing",
  context: "...",
});
```

## Context Helpers

Tag all spans within a callback with session/user metadata:

```typescript
await arthur.session("session-123", async () => {
  // All spans created here will have session.id = "session-123"
  await doWork();
});

await arthur.user("user-42", async () => {
  // All spans created here will have user.id = "user-42"
  await doWork();
});

await arthur.attributes(
  { sessionId: "s1", userId: "u1", tags: ["prod"] },
  async () => {
    await doWork();
  },
);
```

## Supported Instrumentors

| Method | npm Package |
|--------|-------------|
| `instrumentOpenAI()` | `@arizeai/openinference-instrumentation-openai` |
| `instrumentAnthropic()` | `@arizeai/openinference-instrumentation-anthropic` |
| `instrumentLangchain()` | `@arizeai/openinference-instrumentation-langchain` |
| `instrumentClaudeAgentSdk()` | `@arizeai/openinference-instrumentation-claude-agent-sdk` |
| `instrumentVercelAI()` | `@arizeai/openinference-instrumentation-vercel-ai` |
| `instrumentGroq()` | `@arizeai/openinference-instrumentation-groq` |
| `instrumentMistralAI()` | `@arizeai/openinference-instrumentation-mistralai` |
| `instrumentBeeAgent()` | `@arizeai/openinference-instrumentation-bee-agent` |

### Mastra Integration

For [Mastra](https://mastra.ai) applications, use the dedicated `ArthurExporter` which implements Mastra's `AITracingExporter` interface:

```typescript
import { Arthur } from "@arthur-ai/observability-sdk";
import { ArthurExporter } from "@arthur-ai/observability-sdk/mastra";
import { Mastra } from "@mastra/core";

// Option 1: Create exporter from Arthur instance
const arthur = new Arthur({
  apiKey: "your-api-key",
  taskId: "<your-task-uuid>",
  serviceName: "my-agent",
});
const exporter = arthur.createMastraExporter();

// Option 2: Create exporter directly
const exporter = new ArthurExporter({
  url: "http://localhost:3030",
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

Requires `@mastra/core` as a peer dependency:

```bash
npm install @mastra/core
```

Install the corresponding package to enable each instrumentor:

```bash
npm install @arizeai/openinference-instrumentation-openai
```

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Type check
npm run type-check

# Build (CJS + ESM + .d.ts)
npm run build

# Lint + format check
npm run check
```
