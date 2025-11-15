import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import TuneIcon from "@mui/icons-material/Tune";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import React, { memo, useCallback, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptType } from "../types";

import ModelParamsDialog from "./ModelParamsDialog";

interface ManagementButtonsProps {
  prompt: PromptType;
  setSavePromptOpen: (open: boolean) => void;
}

const ManagementButtons = ({ prompt, setSavePromptOpen }: ManagementButtonsProps) => {
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const { dispatch } = usePromptContext();

  const handleRunPrompt = useCallback(() => {
    dispatch({
      type: "runPrompt",
      payload: { promptId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleDuplicatePrompt = useCallback(() => {
    dispatch({
      type: "duplicatePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleParamsModelOpen = useCallback(() => {
    setParamsModelOpen(true);
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

  const runDisabled = prompt.running || prompt.modelName === "";
  const isDirty = prompt.isDirty;
  const saveTooltip = isDirty ? "Save unsaved changes" : "Save Prompt";

  return (
    <>
      <Tooltip title="Run Prompt" placement="top-start" arrow>
        <span>
          <IconButton aria-label="run prompt" onClick={handleRunPrompt} disabled={runDisabled} loading={prompt.running}>
            <PlayArrowIcon color={runDisabled ? "disabled" : "success"} />
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

const arePropsEqual = (prevProps: ManagementButtonsProps, nextProps: ManagementButtonsProps): boolean => {
  // Only re-render if relevant prompt fields change
  return (
    prevProps.prompt.id === nextProps.prompt.id &&
    prevProps.prompt.running === nextProps.prompt.running &&
    prevProps.prompt.modelName === nextProps.prompt.modelName &&
    prevProps.prompt.name === nextProps.prompt.name &&
    prevProps.prompt.modelParameters === nextProps.prompt.modelParameters &&
    prevProps.prompt.isDirty === nextProps.prompt.isDirty &&
    prevProps.setSavePromptOpen === nextProps.setSavePromptOpen
  );
};

export default memo(ManagementButtons, arePropsEqual);
