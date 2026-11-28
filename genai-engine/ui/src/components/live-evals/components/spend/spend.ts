import { type DisplayCurrency, formatCost } from "@arthur/shared-components";

import { sampleRateToPercent } from "../sample-rate";

import type { ContinuousEvalDailySpendEstimate, ContinuousEvalSpendResponse, SpendEstimateUnavailableReason } from "@/lib/api-client/api-client";

const formatTracesPerDay = (tracesPerDay: number): string => tracesPerDay.toLocaleString(undefined, { maximumFractionDigits: 1 });

// traces/day × sample rate × average run cost, with the numbers the backend used.
export const describeEstimateFormula = (estimate: ContinuousEvalDailySpendEstimate, currency: DisplayCurrency): string => {
  const parts = [`${formatTracesPerDay(estimate.traces_per_day)} traces/day`, `${sampleRateToPercent(estimate.sample_rate)}% sampled`];
  const judgedShare = estimate.judged_share ?? 1;
  if (judgedShare < 1) parts.push(`${sampleRateToPercent(judgedShare)}% reach the judge`);
  if (estimate.average_run_cost != null) parts.push(`${formatCost(estimate.average_run_cost, currency)} per run`);
  const pricedFrom = estimate.priced_since ? `, runs since the evaluator changed` : "";
  return `${parts.join(" × ")} (last ${estimate.window_days} days${pricedFrom})`;
};

export const describeUnavailableEstimate = (
  reason: SpendEstimateUnavailableReason | null | undefined,
  windowDays: number,
  unpricedRunCount = 0,
  pricedSince: string | null = null
): string => {
  if (reason === "no_traces") return `No traces in the last ${windowDays} days`;
  // The judge was called, but its model has no price, so there is no cost to average.
  if (unpricedRunCount > 0) {
    return `${unpricedRunCount} runs called the LLM ${pricedSince ? "since the evaluator changed" : `in the last ${windowDays} days`}, but its model has no price`;
  }
  // Only runs from the current evaluator are priced, so older runs don't count.
  if (pricedSince) return "No runs since the evaluator changed";
  return `No runs that called the LLM in the last ${windowDays} days`;
};

const isNumberOrNull = (value: unknown): boolean => value == null || typeof value === "number";

// The generated types only hold at compile time. A 200 with another shape would throw mid-render and blank the app,
// so callers render nothing for it, as they do for a failed request.
export const isSpendEstimate = (value: unknown): value is ContinuousEvalDailySpendEstimate => {
  if (typeof value !== "object" || value === null) return false;
  const estimate = value as Record<string, unknown>;
  return (
    typeof estimate.window_days === "number" &&
    typeof estimate.traces_per_day === "number" &&
    typeof estimate.sample_rate === "number" &&
    isNumberOrNull(estimate.estimated_daily_cost) &&
    isNumberOrNull(estimate.average_run_cost) &&
    (estimate.unavailable_reason == null || typeof estimate.unavailable_reason === "string")
  );
};

export const isSpendResponse = (value: unknown): value is ContinuousEvalSpendResponse => {
  if (typeof value !== "object" || value === null) return false;
  const spend = value as Record<string, unknown>;
  return typeof spend.last_24h_run_count === "number" && typeof spend.last_24h_cost === "number" && isSpendEstimate(spend.estimate);
};
