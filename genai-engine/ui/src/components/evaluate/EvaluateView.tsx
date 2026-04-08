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

import Evaluators from "@/components/evaluators/Evaluators";
import { Results } from "@/components/live-evals/components/results";
import MLEvaluators from "@/components/ml-evaluators/MLEvaluators";
import { FilterStoreProvider } from "@/components/traces/stores/filter.store";

type EvaluateTab = "evaluators" | "ml-evals-management" | "results";

export const EvaluateView = () => {
  const [isEvalsModalOpen, setIsEvalsModalOpen] = useState(false);
  const [isMLEvalsModalOpen, setIsMLEvalsModalOpen] = useState(false);

  const [activeTab, setActiveTab] = useQueryState(
    "section",
    parseAsStringEnum<EvaluateTab>(["evaluators", "ml-evals-management", "results"]).withDefault("evaluators")
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
          {activeTab === "evaluators" && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsEvalsModalOpen(true)}>
              Evaluator
            </Button>
          )}
          {activeTab === "ml-evals-management" && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsMLEvalsModalOpen(true)}>
              ML Evaluator
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
        <Tab label="Evaluators" value="evaluators" />
        <Tab label="ML Evals" value="ml-evals-management" />
        <Tab label="Results" value="results" />
      </Tabs>

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {activeTab === "evaluators" && (
          <Evaluators
            embedded
            isCreateModalOpen={isEvalsModalOpen}
            onCreateModalOpen={() => setIsEvalsModalOpen(true)}
            onCreateModalClose={() => setIsEvalsModalOpen(false)}
          />
        )}
        {activeTab === "ml-evals-management" && (
          <MLEvaluators
            isCreateModalOpen={isMLEvalsModalOpen}
            onCreateModalClose={() => setIsMLEvalsModalOpen(false)}
          />
        )}
        {activeTab === "results" && (
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
