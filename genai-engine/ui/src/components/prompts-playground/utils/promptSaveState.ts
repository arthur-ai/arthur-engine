import { PromptType } from "../types";

/**
 * Extracts and normalizes only the fields that constitute the "saveable content"
 * of a prompt. Returns a stable JSON string for snapshot comparison.
 *
 * Excludes transient/UI-only fields: id, classification, created_at, running,
 * runResponse, version, isDirty, needsSave, savedSnapshot.
 */
export function getPromptSaveableFields(prompt: PromptType): string {
  const normalized = {
    name: prompt.name,
    modelName: prompt.modelName,
    modelProvider: prompt.modelProvider,
    messages: prompt.messages.map((m) => ({
      role: m.role,
      content: m.content,
      tool_calls: m.tool_calls ?? null,
    })),
    modelParameters: {
      temperature: prompt.modelParameters.temperature ?? null,
      top_p: prompt.modelParameters.top_p ?? null,
      timeout: prompt.modelParameters.timeout ?? null,
      stream: prompt.modelParameters.stream ?? true,
      stream_options: prompt.modelParameters.stream_options ?? null,
      max_tokens: prompt.modelParameters.max_tokens ?? null,
      max_completion_tokens: prompt.modelParameters.max_completion_tokens ?? null,
      frequency_penalty: prompt.modelParameters.frequency_penalty ?? null,
      presence_penalty: prompt.modelParameters.presence_penalty ?? null,
      stop: prompt.modelParameters.stop ?? null,
      seed: prompt.modelParameters.seed ?? null,
      reasoning_effort: prompt.modelParameters.reasoning_effort ?? null,
      logprobs: prompt.modelParameters.logprobs ?? null,
      top_logprobs: prompt.modelParameters.top_logprobs ?? null,
      logit_bias: prompt.modelParameters.logit_bias ?? null,
      thinking: prompt.modelParameters.thinking ?? null,
    },
    tools: prompt.tools.map((t) => ({
      type: t.type,
      function: {
        name: t.function.name,
        description: t.function.description,
        parameters: t.function.parameters,
      },
      strict: t.strict ?? false,
    })),
    toolChoice: prompt.toolChoice ?? null,
    responseFormat: prompt.responseFormat ?? null,
  };
  return JSON.stringify(normalized);
}

/**
 * Derives the dirty/save state of a prompt by comparing its current saveable
 * fields against the savedSnapshot taken at its last save/load point.
 *
 * - isNew: prompt has never been saved (no version)
 * - isDirty: prompt has been modified from its saved version
 * - needsSave: prompt either has unsaved modifications OR is new with user content
 */
export function computePromptDirtyState(prompt: PromptType): {
  isNew: boolean;
  isDirty: boolean;
  needsSave: boolean;
} {
  const isNew = prompt.version == null;
  const isDirty = !isNew && prompt.savedSnapshot != null && getPromptSaveableFields(prompt) !== prompt.savedSnapshot;
  const hasContent =
    isNew &&
    (prompt.messages.some((m) => typeof m.content === "string" && m.content.length > 0) || prompt.modelProvider !== "" || prompt.tools.length > 0);
  return { isNew, isDirty, needsSave: isDirty || hasContent };
}
