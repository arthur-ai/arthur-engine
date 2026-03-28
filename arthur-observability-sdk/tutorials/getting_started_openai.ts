/**
 * Getting started: send one trace to Arthur using the OpenAI Node SDK.
 *
 * Install dependencies:
 *   npm install @arthur-ai/observability-sdk @arthur-ai/observability-sdk[openai] openai tsx
 *
 * Fill in the values below, then run:
 *   npx tsx tutorials/getting_started_openai.ts
 */

import { Arthur } from "@arthur-ai/observability-sdk";
import OpenAI from "openai";

// ── Configure these ──────────────────────────────────────────────────────────
const ARTHUR_BASE_URL = "YOUR_ARTHUR_URL";
const ARTHUR_API_KEY = "YOUR_ARTHUR_API_KEY";
const OPENAI_API_KEY = "YOUR_OPENAI_API_KEY";
// Optional — will be auto-created if omitted
// const ARTHUR_TASK_ID = "your-task-id";
// ─────────────────────────────────────────────────────────────────────────────

const arthur = new Arthur({
  apiKey: ARTHUR_API_KEY,
  baseUrl: ARTHUR_BASE_URL,
  serviceName: "getting-started-ts-openai",
});
arthur.instrumentOpenAI();

const client = new OpenAI({ apiKey: OPENAI_API_KEY });

async function main() {
  const response = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: "Say hello in one sentence." }],
  });

  console.log(response.choices[0].message.content);

  await arthur.shutdown();
}

main().catch(console.error);
