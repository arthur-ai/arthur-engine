import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import SettingsIcon from "@mui/icons-material/Settings";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useEffect, useState } from "react";

import MessagesSection from "./MessagesSection";
import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import PromptSelectors from "./PromptSelectors";
import { usePromptContext } from "./PromptsPlaygroundContext";
import SavePromptDialog from "./SavePromptDialog";
import Tools from "./Tools";
import { PromptComponentProps } from "./types";

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt }: PromptComponentProps) => {
  // This name value updates when an existing prompt is selected
  const [currentPromptName, setCurrentPromptName] = useState<string>(
    prompt.name || ""
  );
  const [nameInputValue, setNameInputValue] = useState("");
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const [savePromptOpen, setSavePromptOpen] = useState<boolean>(false);

  const { dispatch } = usePromptContext();

  const handleSavePromptOpen = () => {
    setSavePromptOpen(true);
  };

  const handleDeletePrompt = useCallback(() => {
    dispatch({
      type: "deletePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleDuplicatePrompt = useCallback(() => {
    dispatch({
      type: "duplicatePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleParamsModelOpen = () => {
    setParamsModelOpen(true);
  };

  useEffect(() => {
    setNameInputValue(currentPromptName);
  }, [currentPromptName]);

  return (
    <div className="min-h-[500px] shadow-md rounded-lg p-4">
      <Container
        component="div"
        className="p-1 mt-1"
        maxWidth="xl"
        disableGutters
      >
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-1">
          <div className="flex justify-start items-center gap-1">
            <PromptSelectors
              prompt={prompt}
              currentPromptName={currentPromptName}
              onPromptNameChange={setCurrentPromptName}
            />
          </div>
          <div className="flex justify-end items-center gap-1">
            <Tooltip title="Duplicate Prompt" placement="top-start" arrow>
              <IconButton
                aria-label="duplicate"
                onClick={handleDuplicatePrompt}
              >
                <ContentCopyIcon color="secondary" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Model Parameters" placement="top-start" arrow>
              <IconButton
                aria-label="model parameters"
                onClick={handleParamsModelOpen}
              >
                <SettingsIcon color="info" />
              </IconButton>
            </Tooltip>
            <ModelParamsDialog
              open={paramsModelOpen}
              setOpen={setParamsModelOpen}
              promptId={prompt.id}
              name={prompt.name}
              modelParameters={prompt.modelParameters}
            />
            <Tooltip title="Save Prompt" placement="top-start" arrow>
              <IconButton aria-label="save" onClick={handleSavePromptOpen}>
                <SaveIcon color="primary" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete Prompt" placement="top-start" arrow>
              <IconButton aria-label="delete" onClick={handleDeletePrompt}>
                <DeleteIcon color="error" />
              </IconButton>
            </Tooltip>
          </div>
        </div>
      </Container>
      <div className="m-1">
        <Paper elevation={2} className="p-1">
          <MessagesSection prompt={prompt} />
        </Paper>
      </div>
      <div className="m-1">
        <Paper elevation={2} className="p-1">
          <Tools prompt={prompt} />
        </Paper>
      </div>
      <div className="m-1">
        <Paper elevation={2} className="p-1">
          <OutputField
            promptId={prompt.id}
            outputField={prompt.outputField}
            responseFormat={prompt.responseFormat}
          />
        </Paper>
      </div>
      <SavePromptDialog
        open={savePromptOpen}
        setOpen={setSavePromptOpen}
        prompt={prompt}
        initialName={nameInputValue}
      />
    </div>
  );
};

export default Prompt;
