import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { Skeleton, Stack, Typography } from "@mui/material";

import { StatCard } from "../../[evalId]/StatCard";
import { useContinuousEvalSpend, useContinuousEvalSpendEstimate } from "../../hooks/useContinuousEvalSpend";
import { percentToSampleRate, samplePercentSchema } from "../sample-rate";

import { describeEstimateFormula, describeUnavailableEstimate, formatSpend, isSpendEstimate, isSpendResponse } from "./spend";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { ContinuousEvalDailySpendEstimate, ContinuousEvalSpendResponse } from "@/lib/api-client/api-client";

export { describeEstimateFormula, describeUnavailableEstimate, formatSpend } from "./spend";

export const SpendCards = ({ spend, currency }: { spend: ContinuousEvalSpendResponse; currency: string }) => {
  const { estimate } = spend;
  const runs = spend.last_24h_run_count;
  return (
    <Stack direction={{ xs: "column", md: "row" }} sx={{ gap: 2 }}>
      <StatCard
        icon={<PaidOutlinedIcon />}
        label="Last 24 hours"
        value={formatSpend(spend.last_24h_cost, currency)}
        subValue={`${runs.toLocaleString()} ${runs === 1 ? "run" : "runs"}`}
      />
      <StatCard
        icon={<TrendingUpIcon />}
        label="Estimated per day"
        value={estimate.estimated_daily_cost != null ? formatSpend(estimate.estimated_daily_cost, currency) : "—"}
        subValue={
          estimate.estimated_daily_cost != null
            ? describeEstimateFormula(estimate, currency)
            : describeUnavailableEstimate(estimate.unavailable_reason, estimate.window_days, estimate.unpriced_run_count, estimate.priced_since)
        }
      />
    </Stack>
  );
};

export const ContinuousEvalSpendCards = ({ evalId }: { evalId: string }) => {
  const { defaultCurrency } = useDisplaySettings();
  const { data: spend, isLoading } = useContinuousEvalSpend(evalId);

  if (isLoading) {
    return (
      <Stack direction={{ xs: "column", md: "row" }} sx={{ gap: 2 }}>
        <Skeleton variant="rounded" height={104} sx={{ flex: 1 }} />
        <Skeleton variant="rounded" height={104} sx={{ flex: 1 }} />
      </Stack>
    );
  }
  // Spend is supplementary: if it fails to load or comes back malformed, the rest of the page still works.
  if (!isSpendResponse(spend)) return null;

  return <SpendCards spend={spend} currency={defaultCurrency} />;
};

export const SpendEstimateText = ({ estimate, currency }: { estimate: ContinuousEvalDailySpendEstimate; currency: string }) => (
  <Stack direction="row" sx={{ alignItems: "center", gap: 1, color: "text.secondary" }}>
    <PaidOutlinedIcon fontSize="small" />
    <Typography variant="body2" sx={{ color: "text.secondary" }}>
      {estimate.estimated_daily_cost != null ? (
        <>
          Estimated{" "}
          <Typography component="span" variant="body2" sx={{ color: "text.primary", fontWeight: 600 }}>
            {formatSpend(estimate.estimated_daily_cost, currency)} per day
          </Typography>
          : {describeEstimateFormula(estimate, currency)}
        </>
      ) : (
        `No cost estimate yet. ${describeUnavailableEstimate(estimate.unavailable_reason, estimate.window_days, estimate.unpriced_run_count)}${
          estimate.unavailable_reason === "no_runs" ? " for this evaluator on this task." : "."
        }`
      )}
    </Typography>
  </Stack>
);

type SpendEstimateLineProps = {
  taskId: string;
  llmEvalName: string | null;
  llmEvalVersion: string | null;
  samplePercent: string;
};

// Estimate shown under the evaluator on the create forms; follows the evaluator, its version and the sample rate fields.
export const SpendEstimateLine = ({ taskId, llmEvalName, llmEvalVersion, samplePercent }: SpendEstimateLineProps) => {
  const { defaultCurrency } = useDisplaySettings();
  const debouncedPercent = useDebouncedValue(samplePercent);
  const sampleRate = samplePercentSchema.safeParse(debouncedPercent).success ? percentToSampleRate(debouncedPercent) : undefined;
  const { data: estimate, isFetching } = useContinuousEvalSpendEstimate(taskId, llmEvalName, llmEvalVersion, sampleRate);

  if (!llmEvalName || sampleRate === undefined) return null;
  if (!estimate) {
    return isFetching ? <Skeleton variant="text" width={360} /> : null;
  }
  if (!isSpendEstimate(estimate)) return null;
  return <SpendEstimateText estimate={estimate} currency={defaultCurrency} />;
};
