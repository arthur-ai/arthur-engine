import { openai } from "@ai-sdk/openai";
import { anthropic } from "@ai-sdk/anthropic";
import { google } from "@ai-sdk/google";

const providers = {
  openai: (modelName) => openai(modelName),
  anthropic: (modelName) => anthropic(modelName),
  gemini: (modelName) => google(modelName),
};

/**
 * Resolves an Arthur model provider string and model name to an AI SDK model instance.
 * Supports "openai", "anthropic", and "gemini" — matching the providers configured
 * in Arthur Engine.
 *
 *   resolveModel(modelProvider, modelName)
 *     Maps an Arthur prompt's `model_provider` and `model_name` fields to the
 *     corresponding AI SDK model instance (e.g. resolveModel("openai", "gpt-4o")).
 *     Throws if the provider is not recognized.
 */
export function resolveModel(modelProvider, modelName) {
  const provider = providers[modelProvider];

  if (!provider) {
    throw new Error(
      `Unsupported model provider "${modelProvider}". Supported: ${Object.keys(providers).join(", ")}`
    );
  }

  return provider(modelName);
}

/**
 * Creates a lightweight Arthur GenAI Engine API client configured from environment variables.
 *
 * The client exposes a single method:
 *
 *   getPromptByTag(promptName, tag)
 *     Fetches a versioned agentic prompt by name and tag (e.g. "production") from the Arthur
 *     Engine. Returns the full prompt object, including a `messages` array in OpenAI format
 *     (system, user, and assistant turns), the model name and provider to use for inference,
 *     the prompt version number, and any tags applied to that version.
 */
function createArthurClient() {
  const baseUrl = process.env.ARTHUR_BASE_URL ?? "http://localhost:3030";
  const apiKey = process.env.ARTHUR_API_KEY;
  const taskId = process.env.ARTHUR_TASK_ID;

  if (!apiKey) throw new Error("Missing ARTHUR_API_KEY in .env");
  if (!taskId) throw new Error("Missing ARTHUR_TASK_ID in .env");

  async function getPromptByTag(promptName, tag) {
    const url = `${baseUrl}/api/v1/tasks/${taskId}/prompts/${promptName}/versions/tags/${tag}`;

    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${apiKey}` },
    });

    if (res.status === 422) {
      const err = await res.json();
      throw new Error(`Arthur validation error: ${JSON.stringify(err.detail)}`);
    }

    if (!res.ok) throw new Error(`Arthur API error — HTTP ${res.status}`);

    return res.json();
  }

  return { getPromptByTag };
}

export const arthurClient = createArthurClient();
