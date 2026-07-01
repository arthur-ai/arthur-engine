import { Box, LinearProgress, Paper, Stack, Typography } from "@mui/material";

import { getEvalCounts, getRateColor } from "./helpers";

import type { AgenticExperimentDetail, AgenticEvalResultSummaries } from "@/lib/api-client/api-client";

type Props = {
  experiment: AgenticExperimentDetail;
};

const EvalSummaryCard = ({ summary }: { summary: AgenticEvalResultSummaries }) => {
  const { passCount, totalCount } = getEvalCounts(summary);
  const percentage = totalCount > 0 ? (passCount / totalCount) * 100 : 0;
  const barColor = `${getRateColor(percentage)}.main`;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack gap={1}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
          <Typography variant="subtitle2" fontWeight={600} color="text.primary" className="truncate">
            {summary.eval_name} (v{summary.eval_version})
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {percentage.toFixed(0)}%
          </Typography>
        </Stack>

        <LinearProgress
          variant="determinate"
          value={percentage}
          sx={{ height: 8, borderRadius: 1, "& .MuiLinearProgress-bar": { backgroundColor: barColor } }}
        />

        <Typography variant="caption" color="text.secondary">
          {passCount} / {totalCount} test cases passed
        </Typography>
      </Stack>
    </Paper>
  );
};

/**
 * "Overall Eval Performance" section for the agent experiment detail page.
 * One card per eval, mirroring Prompt Runs' overall performance but flattened
 * (agent summaries are one-per-eval rather than one-per-prompt).
 */
export const ExperimentEvalSummary = ({ experiment }: Props) => {
  const evalSummaries = experiment.summary_results.eval_summaries;

  return (
    <Stack gap={1}>
      <Typography variant="h6" color="text.primary" fontWeight="bold">
        Overall Eval Performance
      </Typography>

      {evalSummaries.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="body2" color="text.secondary" fontStyle="italic">
            Eval performance will be shown when the experiment finishes executing test cases.
          </Typography>
        </Paper>
      ) : (
        <Box className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {evalSummaries.map((summary) => (
            <EvalSummaryCard key={`${summary.eval_name}-${summary.eval_version}-${summary.transform_id}`} summary={summary} />
          ))}
        </Box>
      )}
    </Stack>
  );
};
