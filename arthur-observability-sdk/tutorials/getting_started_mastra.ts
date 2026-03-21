/**
 * Getting started: Mastra agent with Arthur observability.
 *
 * Install dependencies:
 *   npm install @arthur-ai/observability-sdk @mastra/core @mastra/observability @ai-sdk/openai tsx
 *
 * Fill in the values below, then run:
 *   npx tsx tutorials/getting_started_mastra.ts
 */

import { Agent } from "@mastra/core/agent";
import { Mastra } from "@mastra/core/mastra";
import { Observability } from "@mastra/observability";
import { ArthurExporter } from "@arthur-ai/observability-sdk/mastra";
import { openai } from "@ai-sdk/openai";

// ── Configure these ──────────────────────────────────────────────────────────
const ARTHUR_BASE_URL = "YOUR_ARTHUR_URL";
const ARTHUR_API_KEY = "YOUR_ARTHUR_API_KEY";
const ARTHUR_TASK_ID = "YOUR_ARTHUR_TASK_ID";
// Set OPENAI_API_KEY in your environment
// ─────────────────────────────────────────────────────────────────────────────

const greeterAgent = new Agent({
  name: "greeter",
  model: openai("gpt-4o-mini"),
  instructions: "You are a friendly assistant. Keep responses brief.",
});

const mastra = new Mastra({
  agents: { greeterAgent },
  observability: new Observability({
    configs: {
      arthur: {
        serviceName: "getting-started-mastra",
        exporters: [
          new ArthurExporter({
            serviceName: "getting-started-mastra",
            url: ARTHUR_BASE_URL,
            apiKey: ARTHUR_API_KEY,
            taskId: ARTHUR_TASK_ID,
          }),
        ],
      },
    },
  }),
});

async function main() {
  const agent = mastra.getAgent("greeterAgent");

  const response = await agent.generate([
    { role: "user", content: "Say hello in one sentence." },
  ]);

  console.log(response.text);
}

main();
