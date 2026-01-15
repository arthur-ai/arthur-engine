import { Stack, Typography, Paper, Skeleton } from "@mui/material";

import { useAgentExperiment } from "@/components/agent-experiments/hooks/useAgentExperiment";
import { Highlight } from "@/components/common/Highlight";

type Props = {
  experimentId: string;
};

export const ExperimentHttpTemplate = ({ experimentId }: Props) => {
  const { data: experiment } = useAgentExperiment(experimentId);

  if (!experiment) {
    return (
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" color="text.primary" fontWeight="bold" mb={2}>
          Endpoint
        </Typography>
        <Skeleton variant="text" width="100%" height={24} />
      </Paper>
    );
  }

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Typography variant="h6" color="text.primary" fontWeight="bold" mb={2}>
        Endpoint
      </Typography>
      <Stack gap={1}>
        <Typography variant="body2" color="text.secondary">
          <span className="font-bold">Name:</span> {experiment.http_template.endpoint_name}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          <span className="font-bold">URL:</span> {experiment.http_template.endpoint_url}
        </Typography>
        {experiment.http_template.headers && experiment.http_template.headers.length > 0 && (
          <Stack gap={0.5}>
            <Typography variant="body2" color="text.secondary" fontWeight="bold">
              Headers:
            </Typography>
            <Stack component="ul" sx={{ m: 0, pl: 3 }}>
              {experiment.http_template.headers.map((header, index) => (
                <Typography key={index} component="li" variant="body2" color="text.secondary" sx={{ fontFamily: "monospace" }}>
                  {header.name}: {header.value}
                </Typography>
              ))}
            </Stack>
          </Stack>
        )}
        {experiment.http_template.request_body && Object.keys(experiment.http_template.request_body).length > 0 && (
          <Stack gap={0.5}>
            <Typography variant="body2" color="text.secondary" fontWeight="bold">
              Request Body:
            </Typography>
            <Highlight code={JSON.stringify(experiment.http_template.request_body, null, 2)} language="json" />
          </Stack>
        )}
      </Stack>
    </Paper>
  );
};
