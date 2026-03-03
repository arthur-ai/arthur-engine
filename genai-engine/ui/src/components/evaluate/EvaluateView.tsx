import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { Suspense, useState } from "react";
import { Link } from "react-router-dom";

import Evaluators from "@/components/evaluators/Evaluators";
import { Management } from "@/components/live-evals/components/management";
import { Results } from "@/components/live-evals/components/results";
import { FilterStoreProvider } from "@/components/traces/stores/filter.store";
import { useTask } from "@/hooks/useTask";

type EvaluateTab = "evals-management" | "ce-management" | "ce-results";

export const EvaluateView = () => {
  const { task } = useTask();
  const [isEvalsModalOpen, setIsEvalsModalOpen] = useState(false);

  const [activeTab, setActiveTab] = useQueryState(
    "section",
    parseAsStringEnum<EvaluateTab>(["evals-management", "ce-management", "ce-results"]).withDefault("evals-management")
  );

  return (
    <Box
      sx={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.default",
        overflow: "hidden",
      }}
    >
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
        <Stack direction="row" alignItems="flex-start" justifyContent="space-between">
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              Evaluate
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Manage evaluators and monitor continuous evaluation performance
            </Typography>
          </Box>
          {activeTab === "evals-management" && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsEvalsModalOpen(true)}>
              Evaluator
            </Button>
          )}
          {(activeTab === "ce-management" || activeTab === "ce-results") && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} component={Link} to={`/tasks/${task?.id}/continuous-evals/new`}>
              Continuous Eval
            </Button>
          )}
        </Stack>
      </Box>

      <Tabs
        variant="fullWidth"
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Evals Management" value="evals-management" />
        <Tab label="Continuous Evals" value="ce-management" />
        <Tab label="Results" value="ce-results" />
      </Tabs>

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {activeTab === "evals-management" && (
          <Evaluators
            embedded
            isCreateModalOpen={isEvalsModalOpen}
            onCreateModalOpen={() => setIsEvalsModalOpen(true)}
            onCreateModalClose={() => setIsEvalsModalOpen(false)}
          />
        )}
        {activeTab === "ce-management" && (
          <Suspense
            fallback={
              <Box sx={{ p: 3 }}>
                <Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />
              </Box>
            }
          >
            <FilterStoreProvider timeRange="3 months">
              <Management />
            </FilterStoreProvider>
          </Suspense>
        )}
        {activeTab === "ce-results" && (
          <Suspense
            fallback={
              <Box sx={{ p: 3 }}>
                <Skeleton variant="rectangular" height="50%" sx={{ borderRadius: 1 }} />
              </Box>
            }
          >
            <FilterStoreProvider timeRange="3 months">
              <Results />
            </FilterStoreProvider>
          </Suspense>
        )}
      </Box>
    </Box>
  );
};
