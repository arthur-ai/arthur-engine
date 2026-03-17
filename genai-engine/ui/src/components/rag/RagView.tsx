import AddIcon from "@mui/icons-material/Add";
import { Box, Button, Stack, Tab, Tabs, Typography } from "@mui/material";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { useRef } from "react";

import { RagExperimentsListView } from "../rag-experiments/RagExperimentsListView";
import RagNotebooks from "../retrievals/notebooks/RagNotebooks";
import { RagConfigurationsPage } from "../retrievals/RagConfigurationsPage";

import { getContentHeight } from "@/constants/layout";

const TAB_VALUES = ["rag-notebooks", "rag-experiments", "rag-configurations"] as const;
type TabValue = (typeof TAB_VALUES)[number];

const TAB_TITLES: Record<TabValue, string> = {
  "rag-notebooks": "RAG Notebooks",
  "rag-experiments": "RAG Experiments",
  "rag-configurations": "RAG Configurations",
};

const TAB_SUBTITLES: Record<TabValue, string> = {
  "rag-notebooks": "Manage and organize your RAG experiment notebooks",
  "rag-experiments": "View and compare results from RAG configuration experiments",
  "rag-configurations": "Manage your RAG provider configurations",
};

const TAB_BUTTON_LABELS: Record<TabValue, string> = {
  "rag-notebooks": "Notebook",
  "rag-experiments": "Experiment",
  "rag-configurations": "Configuration",
};

export const RagView = () => {
  const [activeTab, setActiveTab] = useQueryState("tab", parseAsStringEnum<TabValue>([...TAB_VALUES]).withDefault("rag-notebooks"));

  const notebooksCreateFn = useRef<() => void>(() => {});
  const experimentsCreateFn = useRef<() => void>(() => {});
  const configurationsCreateFn = useRef<() => void>(() => {});

  const registerNotebooksCreate = useRef((fn: () => void) => {
    notebooksCreateFn.current = fn;
  }).current;
  const registerExperimentsCreate = useRef((fn: () => void) => {
    experimentsCreateFn.current = fn;
  }).current;
  const registerConfigurationsCreate = useRef((fn: () => void) => {
    configurationsCreateFn.current = fn;
  }).current;

  const handleCreate = () => {
    if (activeTab === "rag-notebooks") notebooksCreateFn.current();
    else if (activeTab === "rag-experiments") experimentsCreateFn.current();
    else if (activeTab === "rag-configurations") configurationsCreateFn.current();
  };

  return (
    <Box sx={{ width: "100%", height: getContentHeight(), display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Dynamic header */}
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          backgroundColor: "background.paper",
          borderBottom: 1,
          borderColor: "divider",
          flexShrink: 0,
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="h5" fontWeight={600} color="text.primary">
              {TAB_TITLES[activeTab]}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {TAB_SUBTITLES[activeTab]}
            </Typography>
          </Box>
          <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={handleCreate}>
            {TAB_BUTTON_LABELS[activeTab]}
          </Button>
        </Stack>
      </Box>

      {/* Tabs */}
      <Box sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider", flexShrink: 0 }}>
        <Tabs value={activeTab} onChange={(_e, val: TabValue) => setActiveTab(val)} variant="fullWidth" sx={{ backgroundColor: "background.paper" }}>
          <Tab label="Notebooks" value="rag-notebooks" />
          <Tab label="Experiments" value="rag-experiments" />
          <Tab label="Configurations" value="rag-configurations" />
        </Tabs>
      </Box>

      {/* Tab content */}
      <Box sx={{ flex: 1, overflow: "hidden", minHeight: 0 }}>
        <Box sx={{ display: activeTab === "rag-notebooks" ? "flex" : "none", flexDirection: "column", height: "100%" }}>
          <RagNotebooks onRegisterCreate={registerNotebooksCreate} />
        </Box>
        <Box sx={{ display: activeTab === "rag-experiments" ? "flex" : "none", flexDirection: "column", height: "100%" }}>
          <RagExperimentsListView onRegisterCreate={registerExperimentsCreate} />
        </Box>
        <Box sx={{ display: activeTab === "rag-configurations" ? "flex" : "none", flexDirection: "column", height: "100%" }}>
          <RagConfigurationsPage onRegisterCreate={registerConfigurationsCreate} />
        </Box>
      </Box>
    </Box>
  );
};
