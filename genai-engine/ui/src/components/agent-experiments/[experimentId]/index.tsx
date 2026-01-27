import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import { Box, Button, Stack, Typography, Link as MuiLink, ButtonGroup } from "@mui/material";
import { Link, useParams } from "react-router-dom";

import { StatusBadge } from "../components/status-badge";
import { useDeleteAgentExperiment } from "../hooks/useDeleteAgentExperiment";

import { ExperimentHttpTemplate } from "./components/experiment-http-template";
import { ExperimentProgressSummary } from "./components/experiment-progress-summary";
import { TestCases } from "./components/test-cases";
import { usePollAgentExperiment } from "./hooks/usePollAgentExperiment";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { formatDate, formatTimestampDuration } from "@/utils/formatters";

export const AgentExperimentDetail = () => {
  const { task } = useTask();
  const { experimentId } = useParams<{ experimentId: string }>();

  const { data: agentExperiment } = usePollAgentExperiment(experimentId);

  const deleteAgentExperimentMutation = useDeleteAgentExperiment();

  if (!agentExperiment) {
    return <div>Experiment not found</div>;
  }

  return (
    <Stack sx={{ height: getContentHeight() }}>
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack alignItems="flex-start">
            <Button
              component={Link}
              to=".."
              size="small"
              variant="text"
              startIcon={<ArrowBackIcon />}
              color="inherit"
              sx={{ color: "text.primary", mb: 2 }}
            >
              Back to Experiments
            </Button>
            <Stack mb={1}>
              <Stack direction="row" gap={2} alignItems="center">
                <Typography variant="h5" color="text.primary" fontWeight="bold">
                  {agentExperiment.name}
                </Typography>
                <StatusBadge status={agentExperiment.status} />
              </Stack>
              <Typography variant="body2" color="text.secondary">
                {agentExperiment.description}
              </Typography>
            </Stack>
            <Stack direction="row" gap={2}>
              <Typography variant="body2" color="text.secondary">
                <span className="font-bold">Created:</span> {formatDate(agentExperiment.created_at)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <span className="font-bold">Finished:</span> {formatDate(agentExperiment.finished_at)}
              </Typography>
              {agentExperiment.finished_at && (
                <Typography variant="body2" color="text.secondary">
                  <span className="font-bold">Duration:</span> {formatTimestampDuration(agentExperiment.created_at, agentExperiment.finished_at)}
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary">
                <span className="font-bold">Dataset:</span>{" "}
                <MuiLink
                  component={Link}
                  to={`/tasks/${task?.id}/datasets/${agentExperiment.dataset_ref.id}?version=${agentExperiment.dataset_ref.version}`}
                >
                  {agentExperiment.dataset_ref.name} (v{agentExperiment.dataset_ref.version})
                </MuiLink>
              </Typography>
            </Stack>
          </Stack>
          <ButtonGroup>
            <Button
              component={Link}
              to={`/tasks/${task?.id}/agent-experiments/new?template=${experimentId}`}
              variant="outlined"
              color="primary"
              startIcon={<ContentCopyIcon />}
              onClick={() => track(EVENT_NAMES.AGENT_EXPERIMENT_COPIED, { experiment_id: experimentId })}
            >
              Copy to new experiment
            </Button>
            <Button
              loading={deleteAgentExperimentMutation.isPending}
              variant="outlined"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={() => deleteAgentExperimentMutation.mutate(experimentId!)}
            >
              Delete
            </Button>
          </ButtonGroup>
        </Stack>
      </Box>
      <Box overflow="auto">
        <Stack gap={2} p={2}>
          <div className="grid grid-cols-2 gap-4 items-start">
            <ExperimentHttpTemplate experimentId={experimentId!} />
            <ExperimentProgressSummary experiment={agentExperiment} />
          </div>

          <Stack gap={1}>
            <Typography variant="h6" color="text.primary" fontWeight="bold">
              Test Case Results
            </Typography>

            <TestCases experimentId={experimentId!} />
          </Stack>
        </Stack>
      </Box>
    </Stack>
  );
};
