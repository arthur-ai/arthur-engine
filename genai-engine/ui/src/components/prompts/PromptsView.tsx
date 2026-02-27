import { Box, Stack, Tab, Tabs, Typography } from "@mui/material";
import { parseAsStringEnum, useQueryState } from "nuqs";

import Notebooks from "../notebooks/Notebooks";
import { PromptExperimentsView } from "../prompt-experiments/PromptExperimentsView";
import PromptsManagement from "../prompts-management/PromptsManagement";

import { getContentHeight } from "@/constants/layout";

export const PromptsView = () => {
  const [activeTab, setActiveTab] = useQueryState(
    "tab",
    parseAsStringEnum(["notebooks", "prompts-management", "prompt-experiments"]).withDefault("notebooks")
  );

  return (
    <Stack sx={{ height: getContentHeight() }}>
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
            Prompts
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage prompt notebooks, templates, and experiments.
          </Typography>
        </Stack>
      </Stack>
      <Tabs
        variant="fullWidth"
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Prompt Notebooks" value="notebooks" />
        <Tab label="Prompt Management" value="prompts-management" />
        <Tab label="Prompt Experiments" value="prompt-experiments" />
      </Tabs>
      <Box sx={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        {activeTab === "notebooks" && <Notebooks />}
        {activeTab === "prompts-management" && <PromptsManagement />}
        {activeTab === "prompt-experiments" && <PromptExperimentsView />}
      </Box>
    </Stack>
  );
};
