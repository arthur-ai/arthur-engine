import type { AgenticExperimentDetail, AgenticEvalResultSummaries } from "@/lib/api-client/api-client";

export type AggregateEvalRate = {
  passCount: number;
  totalCount: number;
};

/**
 * Sum pass/total across every entry in an eval summary's `eval_results`.
 * Today each summary carries a single entry, but summing keeps the count
 * correct if more are ever returned (instead of silently dropping them).
 */
export const getEvalCounts = (summary: AgenticEvalResultSummaries): AggregateEvalRate =>
  summary.eval_results.reduce<AggregateEvalRate>(
    (acc, result) => ({
      passCount: acc.passCount + result.pass_count,
      totalCount: acc.totalCount + result.total_count,
    }),
    { passCount: 0, totalCount: 0 }
  );

/** Sum pass/total across every eval summary for an at-a-glance pass rate. */
export const getAggregateEvalRate = (experiment: AgenticExperimentDetail): AggregateEvalRate =>
  experiment.summary_results.eval_summaries.reduce<AggregateEvalRate>(
    (acc, summary) => {
      const { passCount, totalCount } = getEvalCounts(summary);
      return { passCount: acc.passCount + passCount, totalCount: acc.totalCount + totalCount };
    },
    { passCount: 0, totalCount: 0 }
  );

export const getRateColor = (percentage: number): "success" | "warning" | "error" => {
  if (percentage >= 80) return "success";
  if (percentage >= 50) return "warning";
  return "error";
};
