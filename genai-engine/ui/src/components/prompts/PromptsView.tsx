import AddIcon from "@mui/icons-material/Add";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import { Box, Button, Menu, MenuItem, Stack, Tab, Tabs, Typography } from "@mui/material";
import { parseAsStringEnum, useQueryState } from "nuqs";
import { useRef, useState } from "react";

import Notebooks from "../notebooks/Notebooks";
import { PromptExperimentsView } from "../prompt-experiments/PromptExperimentsView";
import PromptsManagement from "../prompts-management/PromptsManagement";

import { DATA_TOUR } from "@/components/onboarding/data-tour";
import { useCompleteStep } from "@/components/onboarding/hooks/useCompleteStep";
import { useStepAction } from "@/components/onboarding/hooks/useStepAction";
import { STEP_IDS } from "@/components/onboarding/steps";
import { getContentHeight } from "@/constants/layout";

const TAB_TITLES: Record<string, string> = {
  notebooks: "Prompt Notebooks",
  "prompts-management": "Prompts",
  "prompt-experiments": "Prompt Runs",
};

const TAB_SUBTITLES: Record<string, string> = {
  notebooks: "Manage and organize your prompt experiment notebooks",
  "prompts-management": "Manage and organize your prompts",
  "prompt-experiments": "Test and compare different prompt variations and their effectiveness",
};

export const PromptsView = () => {
  const [activeTab, setActiveTab] = useQueryState(
    "tab",
    parseAsStringEnum(["notebooks", "prompts-management", "prompt-experiments"]).withDefault("notebooks")
  );

  const [experimentsMenuAnchor, setExperimentsMenuAnchor] = useState<null | HTMLElement>(null);
  const experimentButtonRef = useRef<HTMLButtonElement>(null);

  const completeRunExperimentStep = useCompleteStep(STEP_IDS.RUN_EXPERIMENT);
  const completeChooseExperimentTypeStep = useCompleteStep(STEP_IDS.CHOOSE_EXPERIMENT_TYPE);

  // Stable create handler refs — children register their handlers on mount
  const notebooksCreateFn = useRef<() => void>(() => {});
  const promptsCreateFn = useRef<() => void>(() => {});
  const experimentsCreateFn = useRef<() => void>(() => {});
  const experimentsCreateFromExistingFn = useRef<() => void>(() => {});

  const handleCreateNewExperiment = () => {
    setExperimentsMenuAnchor(null);
    experimentsCreateFn.current();
    completeChooseExperimentTypeStep();
  };

  // The tour's Next button funnels through the same code paths the user takes,
  // so completion fires exactly once via the onClick / shared helper.
  useStepAction(STEP_IDS.RUN_EXPERIMENT, () => {
    experimentButtonRef.current?.click();
  });

  useStepAction(STEP_IDS.CHOOSE_EXPERIMENT_TYPE, handleCreateNewExperiment);

  // Stable registration callbacks (extracted from refs so identity never changes)
  const registerNotebooksCreate = useRef((fn: () => void) => {
    notebooksCreateFn.current = fn;
  }).current;
  const registerPromptsCreate = useRef((fn: () => void) => {
    promptsCreateFn.current = fn;
  }).current;
  const registerExperimentsCreate = useRef((fn: () => void) => {
    experimentsCreateFn.current = fn;
  }).current;
  const registerExperimentsCreateFromExisting = useRef((fn: () => void) => {
    experimentsCreateFromExistingFn.current = fn;
  }).current;

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
            {TAB_TITLES[activeTab]}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {TAB_SUBTITLES[activeTab]}
          </Typography>
        </Stack>

        {activeTab === "notebooks" && (
          <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => notebooksCreateFn.current()}>
            Notebook
          </Button>
        )}

        {activeTab === "prompts-management" && (
          <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={() => promptsCreateFn.current()}>
            Prompt
          </Button>
        )}

        {activeTab === "prompt-experiments" && (
          <>
            <Button
              ref={experimentButtonRef}
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              endIcon={<ArrowDropDownIcon />}
              onClick={(e) => {
                setExperimentsMenuAnchor(e.currentTarget);
                completeRunExperimentStep();
              }}
              data-tour={DATA_TOUR.CREATE_EXPERIMENT_BUTTON}
            >
              Experiment
            </Button>
            <Menu
              anchorEl={experimentsMenuAnchor}
              open={Boolean(experimentsMenuAnchor)}
              onClose={() => setExperimentsMenuAnchor(null)}
              anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
              transformOrigin={{ vertical: "top", horizontal: "right" }}
              slotProps={{ paper: { sx: { minWidth: experimentsMenuAnchor?.offsetWidth } } }}
            >
              <MenuItem onClick={handleCreateNewExperiment}>Create New</MenuItem>
              <MenuItem
                onClick={() => {
                  setExperimentsMenuAnchor(null);
                  experimentsCreateFromExistingFn.current();
                  completeChooseExperimentTypeStep();
                }}
              >
                Create from Existing
              </MenuItem>
            </Menu>
          </>
        )}
      </Stack>

      <Tabs
        variant="fullWidth"
        value={activeTab}
        onChange={(_, value) => setActiveTab(value)}
        sx={{ backgroundColor: "background.paper", borderBottom: 1, borderColor: "divider" }}
      >
        <Tab label="Notebooks" value="notebooks" />
        <Tab label="Prompts" value="prompts-management" />
        <Tab label="Runs" value="prompt-experiments" />
      </Tabs>

      <Box sx={{ flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
        {activeTab === "notebooks" && <Notebooks onRegisterCreate={registerNotebooksCreate} />}
        {activeTab === "prompts-management" && <PromptsManagement onRegisterCreate={registerPromptsCreate} />}
        {activeTab === "prompt-experiments" && (
          <PromptExperimentsView onRegisterCreate={registerExperimentsCreate} onRegisterCreateFromExisting={registerExperimentsCreateFromExisting} />
        )}
      </Box>
    </Stack>
  );
};
