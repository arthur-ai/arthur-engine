import type { ReasoningEffortEnum } from "@/lib/api-client/api-client";

// Every reasoning_effort value the backend's schema takes, in strength order.
// Which of them a given model accepts comes from
// GET /api/v1/model_providers/{provider}/reasoning_options.
export const REASONING_EFFORT_OPTIONS: ReasoningEffortEnum[] = ["none", "minimal", "low", "medium", "high", "default"];

// Anthropic's minimum thinking budget.
export const MIN_THINKING_BUDGET_TOKENS = 1024;
