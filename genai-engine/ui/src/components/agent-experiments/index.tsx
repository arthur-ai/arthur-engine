import AddIcon from "@mui/icons-material/Add";
import { Box, Button, ButtonGroup, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";

import { Experiments } from "./components/experiments";

import { getContentHeight } from "@/constants/layout";

interface AgentExperimentsProps {
  embedded?: boolean;
}

export const AgentExperiments = ({ embedded = false }: AgentExperimentsProps) => {
  return (
    <>
      <Stack
        sx={{
          height: embedded ? "100%" : getContentHeight(),
        }}
      >
        {!embedded && (
          <Box
            className="flex flex-col lg:flex-row lg:items-center justify-between gap-4"
            sx={{
              px: 3,
              pt: 3,
              pb: 2,
              borderBottom: 1,
              borderColor: "divider",
              backgroundColor: "background.paper",
            }}
          >
            <div>
              <Typography variant="h5" color="text.primary" fontWeight="bold" mb={0.5}>
                Agent Experiments
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Agent experiments are used to test and optimize agent-based task execution strategies.
              </Typography>
            </div>
            <ButtonGroup size="small" variant="contained" disableElevation>
              {/* <Button startIcon={<AddIcon />} onClick={() => setActiveDialog("endpoint")}>
                New Endpoint
              </Button> */}
              <Button startIcon={<AddIcon />} to={`./new`} component={Link}>
                Experiment
              </Button>
            </ButtonGroup>
          </Box>
        )}
        <Stack sx={{ flex: 1, overflow: "auto" }}>
          <Experiments />
        </Stack>
      </Stack>
    </>
  );
};
