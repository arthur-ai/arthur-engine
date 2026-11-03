import { getLocaleForCurrency } from "@arthur/shared-components";

import { sampleRateToPercent } from "../sample-rate";

import type { ContinuousEvalDailySpendEstimate, SpendEstimateUnavailableReason } from "@/lib/api-client/api-client";
import { formatCurrency } from "@/utils/formatters";

// formatCurrency shows anything under a millionth as "< $0.000001", which reads wrong for no spend at all.
export const formatSpend = (amount: number, currency: string): string =>
  amount === 0
    ? new Intl.NumberFormat(getLocaleForCurrency(currency || "USD"), { style: "currency", currency: currency || "USD" }).format(0)
    : formatCurrency(amount, currency);

const formatTracesPerDay = (tracesPerDay: number): string => tracesPerDay.toLocaleString(undefined, { maximumFractionDigits: 1 });

// traces/day × sample rate × average run cost, with the numbers the backend used.
export const describeEstimateFormula = (estimate: ContinuousEvalDailySpendEstimate, currency: string): string => {
  const parts = [`${formatTracesPerDay(estimate.traces_per_day)} traces/day`, `${sampleRateToPercent(estimate.sample_rate)}% sampled`];
  if (estimate.average_run_cost != null) parts.push(`${formatSpend(estimate.average_run_cost, currency)} per run`);
  return `${parts.join(" × ")} (last ${estimate.window_days} days)`;
};

export const describeUnavailableEstimate = (reason: SpendEstimateUnavailableReason | null | undefined, windowDays: number): string => {
  if (reason === "no_traces") return `No traces in the last ${windowDays} days`;
  return `No runs that called the LLM in the last ${windowDays} days`;
};
