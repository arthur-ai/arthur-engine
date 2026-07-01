import { Chip, Tooltip } from "@mui/material";

import { getAggregateEvalRate, getRateColor } from "./helpers";

import type { AgenticExperimentDetail } from "@/lib/api-client/api-client";

type Props = {
  experiment: AgenticExperimentDetail;
};

/**
 * Compact pass-rate chip shown next to the run status badge. Supplements the
 * execution-only status (Completed/Failed) without changing its meaning.
 * Renders nothing until aggregate eval data exists (populated when the run finishes).
 */
export const EvalStatusChip = ({ experiment }: Props) => {
  const { passCount, totalCount } = getAggregateEvalRate(experiment);

  if (totalCount === 0) {
    return null;
  }

  const percentage = (passCount / totalCount) * 100;

  return (
    <Tooltip title="Aggregate evaluation pass rate across all evals and test cases" arrow>
      <Chip size="small" color={getRateColor(percentage)} variant="outlined" label={`Evals: ${passCount}/${totalCount} passed`} />
    </Tooltip>
  );
};
