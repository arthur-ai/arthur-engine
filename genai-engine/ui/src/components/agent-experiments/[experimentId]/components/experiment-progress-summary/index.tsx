import { LinearProgress, Paper, Stack, Typography } from "@mui/material";

import type { AgenticExperimentDetail } from "@/lib/api-client/api-client";

type Props = {
  experiment: AgenticExperimentDetail;
};

export const ExperimentProgressSummary = ({ experiment }: Props) => {
  const progress = experiment.total_rows > 0 ? (experiment.completed_rows / experiment.total_rows) * 100 : 0;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack gap={2}>
        <Stack>
          <Typography variant="h6" fontWeight="bold">
            Test Case Progress
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {experiment.total_rows} test cases to run. {experiment.completed_rows} completed and {experiment.failed_rows} failed.
          </Typography>
        </Stack>

        <LinearProgress variant="determinate" value={progress} />
      </Stack>
    </Paper>
  );
};
