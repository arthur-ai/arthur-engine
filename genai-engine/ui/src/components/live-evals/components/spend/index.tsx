import PaidOutlinedIcon from "@mui/icons-material/PaidOutlined";
import PauseCircleOutlineOutlinedIcon from "@mui/icons-material/PauseCircleOutlineOutlined";
import TodayOutlinedIcon from "@mui/icons-material/TodayOutlined";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { Alert, Skeleton, Stack, Typography } from "@mui/material";

import { StatCard } from "../../[evalId]/StatCard";
import { useContinuousEvalSpend, useContinuousEvalSpendEstimate } from "../../hooks/useContinuousEvalSpend";
import { percentToSampleRate, samplePercentSchema } from "../sample-rate";
import { spanFilterJson, spanScopeSchema, type SpanScopeValues } from "../span-scope/spanScope";
import { rowsToTraceFilter, traceFilterSchema, type TraceFilterRow } from "../trace-filter";

import { describeEstimateFormula, describeUnavailableEstimate, formatSpend, isSpendEstimate, isSpendResponse } from "./spend";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import type { ContinuousEvalDailySpendEstimate, ContinuousEvalSpendResponse } from "@/lib/api-client/api-client";

export { describeEstimateFormula, describeUnavailableEstimate, formatSpend } from "./spend";

export const SpendCards = ({ spend, currency }: { spend: ContinuousEvalSpendResponse; currency: string }) => {
  const { estimate } = spend;
  const runs = spend.last_24h_run_count;
  const cap = spend.daily_cost_cap_usd;
  return (
    <Stack sx={{ gap: 2 }}>
      {spend.cap_reached && cap != null && (
        <Alert severity="warning" icon={<PauseCircleOutlineOutlinedIcon />}>
          Paused for today: the daily spend cap of {formatSpend(cap, currency)} is reached. New traces are skipped until midnight (engine time, UTC by
          default).
        </Alert>
      )}
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
        {cap != null && (
          <StatCard
            icon={<TodayOutlinedIcon />}
            label="Spent today"
            value={formatSpend(spend.spent_today, currency)}
            subValue={`since midnight, of ${formatSpend(cap, currency)} daily cap`}
            color={spend.cap_reached ? "warning" : "default"}
          />
        )}
      </Stack>
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
  traceFilter?: TraceFilterRow[];
  spanScope?: SpanScopeValues;
};

// Estimate shown under the evaluator on the create forms; follows the evaluator, its version, the sample rate and the trace filter fields.
export const SpendEstimateLine = ({ taskId, llmEvalName, llmEvalVersion, samplePercent, traceFilter = [], spanScope }: SpendEstimateLineProps) => {
  const { defaultCurrency } = useDisplaySettings();
  const debouncedPercent = useDebouncedValue(samplePercent);
  const debouncedFilter = useDebouncedValue(traceFilter);
  const debouncedScope = useDebouncedValue(spanScope);
  const sampleRate = samplePercentSchema.safeParse(debouncedPercent).success ? percentToSampleRate(debouncedPercent) : undefined;
  // A half-filled condition isn't sent; the estimate covers the complete ones.
  const conditions = traceFilterSchema.safeParse(debouncedFilter).success ? rowsToTraceFilter(debouncedFilter) : null;
  const { data: estimate, isFetching } = useContinuousEvalSpendEstimate(
    taskId,
    llmEvalName,
    llmEvalVersion,
    sampleRate,
    conditions ? JSON.stringify(conditions) : null,
    debouncedScope && spanScopeSchema.safeParse(debouncedScope).success ? spanFilterJson(debouncedScope) : null,
    debouncedScope ? Number(debouncedScope.maxSpans) : null
  );

  if (!llmEvalName || sampleRate === undefined) return null;
  if (!estimate) {
    return isFetching ? <Skeleton variant="text" width={360} /> : null;
  }
  if (!isSpendEstimate(estimate)) return null;
  return <SpendEstimateText estimate={estimate} currency={defaultCurrency} />;
};
