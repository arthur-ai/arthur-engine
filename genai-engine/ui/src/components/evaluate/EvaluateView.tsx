import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { Suspense, useState } from "react";

import Evaluators from "@/components/evaluators/Evaluators";
import { Results } from "@/components/live-evals/components/results";
import { FilterStoreProvider } from "@/components/traces/stores/filter.store";

type EvaluateTab = "evaluators" | "results";

export const EvaluateView = () => {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const [activeTab, setActiveTab] = useQueryState("section", parseAsStringEnum<EvaluateTab>(["evaluators", "results"]).withDefault("evaluators"));

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
        <Box sx={{ display: "flex", flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" }}>
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              Evaluate
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Manage evaluators and monitor continuous evaluation performance
            </Typography>
          </Box>
          {activeTab === "evaluators" && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsCreateModalOpen(true)}>
              Evaluator
            </Button>
          )}
        </Box>
      </Box>

      <Tabs
        variant="fullWidth"
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Evaluators" value="evaluators" />
        <Tab label="Results" value="results" />
      </Tabs>

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {activeTab === "evaluators" && (
          <Evaluators
            embedded
            isCreateModalOpen={isCreateModalOpen}
            onCreateModalOpen={() => setIsCreateModalOpen(true)}
            onCreateModalClose={() => setIsCreateModalOpen(false)}
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
