# Mastra 1.x Migration Guide + Arthur Observability SDK Integration

This document covers the changes required to migrate example agents from Mastra 0.x to 1.x and integrate the `@arthur-ai/observability-sdk` for telemetry.

The **analytics-agent** has been fully migrated and can be used as reference.

## 1. Package upgrades

Replace the Mastra 0.x packages with 1.x equivalents and add the Arthur SDK:

```diff
- "@mastra/core": "0.24.0",
- "@mastra/deployer": "^0.24.0",
- "@mastra/libsql": "^0.16.2",
- "@mastra/mcp": "^0.14.2",
- "@mastra/server": "^0.24.0",
+ "@mastra/core": "1.14.0",
+ "@mastra/deployer": "1.14.0",
+ "@mastra/libsql": "^1.7.1",
+ "@mastra/mcp": "^1.3.0",
+ "@mastra/observability": "^1.5.0",
+ "@mastra/server": "1.14.0",
+ "@arthur-ai/observability-sdk": "^1.0.1",
- "mastra": "0.13.4",
+ "mastra": "1.3.13",
```

Mastra 1.x requires **Node 22+** (`nvm install 22`).

## 2. Import renames (`ai-tracing` -> `observability`)

Mastra 1.x renamed the tracing module:

```diff
- import { AISpanType, TracingContext } from "@mastra/core/ai-tracing";
+ import { SpanType, TracingContext } from "@mastra/core/observability";
```

And the enum:

```diff
- type: AISpanType.GENERIC,
+ type: SpanType.GENERIC,
```

## 3. Observability configuration

Mastra 1.x requires the `Observability` wrapper class from `@mastra/observability`. Replace the inline local `ArthurExporter` with the SDK's version:

```diff
- import { ArthurExporter } from "./observability/arthur";
+ import { Observability } from "@mastra/observability";
+ import { ArthurExporter } from "@arthur-ai/observability-sdk/mastra";
```

The config object must be wrapped in `new Observability(...)`:

```diff
- observability: {
+ observability: new Observability({
    configs: {
      arthur: {
        serviceName: "my-agent",
        exporters: [
          new ArthurExporter({
            serviceName: "my-agent",
            url: process.env.ARTHUR_BASE_URL!,
-           headers: {
-             Authorization: `Bearer ${process.env.ARTHUR_API_KEY!}`,
-           },
+           apiKey: process.env.ARTHUR_API_KEY!,
            taskId: process.env.ARTHUR_TASK_ID!,
          }),
        ],
      },
    },
- },
+ }),
```

Key difference: the SDK's `ArthurExporter` takes `apiKey` directly (builds the `Authorization` header internally), whereas the old local exporter required pre-built `headers`.

## 4. LibSQLStore requires `id`

```diff
  storage: new LibSQLStore({
+   id: "my-agent",
    url: ":memory:",
  }),
```

## 5. Tool `execute` signature changed (CRITICAL)

Mastra 1.x changed the tool `execute` function from a single-object parameter to two separate arguments:

```diff
- execute: async ({ context, runtimeContext, mastra, tracingContext }) => {
-   const query = context.userQuery;
+ execute: async (inputData, executionContext) => {
+   const { mastra, runtimeContext, tracingContext } = executionContext ?? {};
+   const query = inputData.userQuery;
```

- **First argument** (`inputData`): the validated input data (what was `context` before)
- **Second argument** (`executionContext`): contains `mastra`, `runtimeContext`, `tracingContext`, `agent`, etc.

Without this change, `mastra?.getAgent(...)` returns `undefined` because `mastra` is destructured from `inputData` (which doesn't have it) instead of `executionContext`.

## 6. Environment variables

Each agent needs these in `.env`:

```
OPENAI_API_KEY=...
ARTHUR_BASE_URL=...
ARTHUR_API_KEY=...
ARTHUR_TASK_ID=...
```

## Agents to migrate

| Agent | Status |
|-------|--------|
| analytics-agent | Done |
| customer-support-agent | Done |
| mastra-translator-agent | Done (version bump only — no observability/tracing to migrate) |
| image-analysis-agent | N/A — not a Mastra agent (pure Next.js + OpenTelemetry) |
| hosted-chatbot | N/A — not a Mastra agent (Python FastAPI + LangChain) |
