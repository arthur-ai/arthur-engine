import AddIcon from "@mui/icons-material/Add";
import { Box, Button, Skeleton, Stack, Tab, Tabs, Typography } from "@mui/material";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { Suspense } from "react";
import { Link } from "react-router-dom";

import { FilterStoreProvider } from "../traces/stores/filter.store";

import { Management } from "./components/management";
import { Results } from "./components/results";

import { getContentHeight } from "@/constants/layout";
import { useTask } from "@/hooks/useTask";

export const LiveEvals = () => {
  const { task } = useTask();

  const [activeTab, setActiveTab] = useQueryState("tab", parseAsStringEnum(["management", "results"]).withDefault("management"));

  return (
    <>
      <Stack
        sx={{
          height: getContentHeight(),
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{
            px: 3,
            pt: 3,
            pb: 2,
            borderBottom: 1,
            borderColor: "divider",
            backgroundColor: "background.paper",
          }}
        >
          <Stack>
            <Typography variant="h5" color="text.primary" fontWeight="bold" mb={0.5}>
              Continuous Evals
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Continuous evals are used to monitor and analyze your model's performance in real-time.
            </Typography>
          </Stack>
          <Button variant="contained" color="primary" startIcon={<AddIcon />} to={`/tasks/${task?.id}/continuous-evals/new`} component={Link}>
            Continuous Eval
          </Button>
        </Stack>
        <Tabs
          variant="fullWidth"
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
          sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
        >
          <Tab label="Management" value="management" />
          <Tab label="Results" value="results" />
        </Tabs>
        {activeTab === "management" && (
          <Suspense
            fallback={
              <Box sx={{ p: 3, flex: 1 }}>
                <Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />
              </Box>
            }
          >
            <FilterStoreProvider timeRange="3 months">
              <Management />
            </FilterStoreProvider>
          </Suspense>
        )}
        {activeTab === "results" && (
          <Suspense
            fallback={
              <Box sx={{ p: 3, flex: 1 }}>
                <Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />
              </Box>
            }
          >
            <FilterStoreProvider timeRange="3 months">
              <Results />
            </FilterStoreProvider>
          </Suspense>
        )}
      </Stack>
    </>
  );
};

export const LiveEvalsSkeleton = () => {
  return (
    <Stack sx={{ height: getContentHeight() }}>
      {/* Header section */}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack>
          <Skeleton variant="text" width={180} height={32} sx={{ mb: 0.5 }} />
          <Skeleton variant="text" width={480} height={20} />
        </Stack>
        <Skeleton variant="rounded" width={180} height={36} />
      </Stack>
    </Stack>
  );
};
