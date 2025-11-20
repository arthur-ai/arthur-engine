import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import TuneIcon from "@mui/icons-material/Tune";
import VisibilityIcon from "@mui/icons-material/Visibility";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import React, { memo, useCallback, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptType } from "../types";

import ModelParamsDialog from "./ModelParamsDialog";
import PreviewPromptModal from "./PreviewPromptModal";

interface ManagementButtonsProps {
  prompt: PromptType;
  setSavePromptOpen: (open: boolean) => void;
}

const ManagementButtons = ({ prompt, setSavePromptOpen }: ManagementButtonsProps) => {
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const [previewModalOpen, setPreviewModalOpen] = useState<boolean>(false);
  const { dispatch, state, experimentConfig, handleRunSingleWithConfig, isRunningExperiment } = usePromptContext();

  const handleRunPrompt = useCallback(() => {
    // If in config mode, run with experiment
    if (experimentConfig && handleRunSingleWithConfig) {
      handleRunSingleWithConfig(prompt.id);
      return;
    }

    // Otherwise, run in normal playground mode
    dispatch({
      type: "runPrompt",
      payload: { promptId: prompt.id },
    });
  }, [dispatch, prompt.id, experimentConfig, handleRunSingleWithConfig]);

  const handleDuplicatePrompt = useCallback(() => {
    dispatch({
      type: "duplicatePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleParamsModelOpen = useCallback(() => {
    setParamsModelOpen(true);
  }, []);

  const handlePreviewOpen = useCallback(() => {
    setPreviewModalOpen(true);
  }, []);

  const handleSavePromptOpen = useCallback(() => {
    setSavePromptOpen(true);
  }, [setSavePromptOpen]);

  const handleDeletePrompt = useCallback(() => {
    dispatch({
      type: "deletePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  // Check if there are any unset variables
  // In config mode, variables can be empty if they're mapped to dataset columns
  const hasUnsetVariables = React.useMemo(() => {
    if (experimentConfig?.prompt_variable_mapping) {
      // Build a set of mapped variable names
      const mappedVariables = new Set<string>();
      experimentConfig.prompt_variable_mapping.forEach((mapping: any) => {
        mappedVariables.add(mapping.variable_name);
      });

      // Check if any unmapped variables are empty
      return Array.from(state.keywords.entries()).some(([key, value]) => {
        const isMapped = mappedVariables.has(key);
        const isEmpty = !value || value.trim() === "";
        return !isMapped && isEmpty; // Only fail if unmapped AND empty
      });
    }

    // Normal mode: all variables must have values
    return Array.from(state.keywords.values()).some((value) => !value || value.trim() === "");
  }, [state.keywords, experimentConfig]);

  // In config mode, disable if experiment is running. In normal mode, disable if prompt is running
  const runDisabled =
    prompt.modelName === "" ||
    hasUnsetVariables ||
    (experimentConfig ? isRunningExperiment : prompt.running);
  const previewDisabled = hasUnsetVariables;
  const isDirty = prompt.isDirty;
  const saveTooltip = isDirty ? "Save unsaved changes" : "Save Prompt";

  // Determine the run button tooltip based on disabled state
  let runTooltip = experimentConfig ? "Run Experiment with this Prompt" : "Run Prompt";
  if (hasUnsetVariables) {
    runTooltip = "Please fill in all variable values before running";
  } else if (prompt.modelName === "") {
    runTooltip = "Please select a model before running";
  } else if (experimentConfig && isRunningExperiment) {
    runTooltip = "An experiment is currently running";
  } else if (prompt.running) {
    runTooltip = "Prompt is currently running";
  }

  // Determine the preview button tooltip
  const previewTooltip = hasUnsetVariables ? "Please fill in all variable values before previewing" : "Preview Rendered Prompt";

  return (
    <>
      <Tooltip title={runTooltip} placement="top-start" arrow>
        <span>
          <IconButton aria-label="run prompt" onClick={handleRunPrompt} disabled={runDisabled} loading={prompt.running}>
            <PlayArrowIcon color={runDisabled ? "disabled" : "success"} />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title={previewTooltip} placement="top-start" arrow>
        <span>
          <IconButton aria-label="preview prompt" onClick={handlePreviewOpen} disabled={previewDisabled}>
            <VisibilityIcon color={previewDisabled ? "disabled" : "info"} />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title="Duplicate Prompt" placement="top-start" arrow>
        <IconButton aria-label="duplicate" onClick={handleDuplicatePrompt}>
          <ContentCopyIcon color="secondary" />
        </IconButton>
      </Tooltip>
      <Tooltip title="Model Parameters" placement="top-start" arrow>
        <IconButton aria-label="model parameters" onClick={handleParamsModelOpen}>
          <TuneIcon color="info" />
        </IconButton>
      </Tooltip>
      <ModelParamsDialog
        open={paramsModelOpen}
        setOpen={setParamsModelOpen}
        promptId={prompt.id}
        name={prompt.name}
        modelParameters={prompt.modelParameters}
      />
      <PreviewPromptModal open={previewModalOpen} setOpen={setPreviewModalOpen} prompt={prompt} />
      <Tooltip title={saveTooltip} placement="top-start" arrow>
        <IconButton
          aria-label="save"
          onClick={handleSavePromptOpen}
          sx={{
            ...(isDirty && {
              backgroundColor: "#f97316",
              "&:hover": {
                backgroundColor: "#ea580c",
              },
            }),
          }}
        >
          <SaveIcon sx={{ color: isDirty ? "white" : undefined }} color={isDirty ? undefined : "primary"} />
        </IconButton>
      </Tooltip>
      <Tooltip title="Delete Prompt" placement="top-start" arrow>
        <IconButton aria-label="delete" onClick={handleDeletePrompt}>
          <DeleteIcon color="error" />
        </IconButton>
      </Tooltip>
    </>
  );
};

// Note: We removed the memo optimization because we now depend on global state.keywords
// which isn't available in props, so we can't properly detect changes in arePropsEqual
export default ManagementButtons;
