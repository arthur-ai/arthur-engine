import AddIcon from "@mui/icons-material/Add";
import { Box, Button, ButtonGroup, Dialog, Skeleton, Stack, Tab, Tabs, Typography } from "@mui/material";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { Activity, Suspense } from "react";

import { Endpoints } from "./components/endpoints";
import { NewEndpointDialogContent } from "./components/endpoints/new-dialog";
import { Experiments } from "./components/experiments";
import { NewExperimentDialogContent } from "./components/experiments/components/new-dialog";

import { getContentHeight } from "@/constants/layout";

export const AgentExperiments = () => {
  const [activeTab, setActiveTab] = useQueryState("tab", parseAsStringEnum(["endpoints", "experiments"]).withDefault("endpoints"));
  const [activeDialog, setActiveDialog] = useQueryState("create", parseAsStringEnum(["endpoint", "experiment"]));

  return (
    <>
      <Stack
        sx={{
          height: getContentHeight(),
        }}
      >
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
            <Button startIcon={<AddIcon />} onClick={() => setActiveDialog("endpoint")}>
              New Endpoint
            </Button>
            <Button startIcon={<AddIcon />} onClick={() => setActiveDialog("experiment")}>
              New Experiment
            </Button>
          </ButtonGroup>
        </Box>
        <Tabs
          variant="fullWidth"
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
          sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
        >
          <Tab label="Endpoints" value="endpoints" />
          <Tab label="Experiments" value="experiments" />
        </Tabs>
        <Activity mode={activeTab === "endpoints" ? "visible" : "hidden"}>
          <Suspense fallback={<Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />}>
            <Endpoints />
          </Suspense>
        </Activity>
        <Activity mode={activeTab === "experiments" ? "visible" : "hidden"}>
          <Suspense fallback={<Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />}>
            <Experiments />
          </Suspense>
        </Activity>
      </Stack>

      <Dialog open={activeDialog === "endpoint"} onClose={() => setActiveDialog(null)} maxWidth="md" fullWidth>
        <NewEndpointDialogContent />
      </Dialog>
      <Dialog open={activeDialog === "experiment"} onClose={() => setActiveDialog(null)} maxWidth="md" fullWidth>
        <NewExperimentDialogContent />
      </Dialog>
    </>
  );
};
