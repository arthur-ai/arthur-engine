import { Box, CircularProgress, Stack, Typography } from "@mui/material";

import { useAgenticNotebookHistory } from "@/components/agent-notebook/hooks/useAgenticNotebookHistory";

type Props = {
  notebookId: string;
};

export const History = ({ notebookId }: Props) => {
  const { data, isLoading } = useAgenticNotebookHistory(notebookId);

  if (isLoading)
    return (
      <Box p={2}>
        <CircularProgress className="mx-auto" />
      </Box>
    );

  return (
    <Stack p={2}>
      <Typography variant="h6" color="text.primary" fontWeight="bold">
        Runs History (latest {data?.data.length} run(s))
      </Typography>
      <Stack>
        {data?.data.map((run) => (
          <Stack key={run.id}>
            <Typography variant="body1" color="text.primary">
              {run.name}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Stack>
  );
};
