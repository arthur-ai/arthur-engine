import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { AgentExperiments } from "@/components/agent-experiments";
import { AgentNotebook } from "@/components/agent-notebook";

type TestTab = "agent-experiments" | "agentic-notebooks";

export const TestView = () => {
  const { id: taskId } = useParams<{ id: string }>();
  const [isNotebookModalOpen, setIsNotebookModalOpen] = useState(false);

  const [activeTab, setActiveTab] = useQueryState(
    "section",
    parseAsStringEnum<TestTab>(["agent-experiments", "agentic-notebooks"]).withDefault("agent-experiments")
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
              Agent Tests
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Run and manage agent experiments and notebooks
            </Typography>
          </Box>
          {activeTab === "agent-experiments" && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} component={Link} to={`/tasks/${taskId}/agent-experiments/new`}>
              Experiment
            </Button>
          )}
          {activeTab === "agentic-notebooks" && (
            <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => setIsNotebookModalOpen(true)}>
              Notebook
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
        <Tab label="Experiments" value="agent-experiments" />
        <Tab label="Notebooks" value="agentic-notebooks" />
      </Tabs>

      <Box sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {activeTab === "agent-experiments" && <AgentExperiments embedded />}
        {activeTab === "agentic-notebooks" && (
          <AgentNotebook
            embedded
            isCreateModalOpen={isNotebookModalOpen}
            onCreateModalOpen={() => setIsNotebookModalOpen(true)}
            onCreateModalClose={() => setIsNotebookModalOpen(false)}
          />
        )}
      </Box>
    </Box>
  );
};
