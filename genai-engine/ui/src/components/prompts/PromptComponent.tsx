import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import SettingsIcon from "@mui/icons-material/Settings";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useEffect, useState } from "react";

import MessageComponent from "./MessageComponent";
import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import { usePromptContext } from "./PromptContext";
import SavePromptDialog from "./SavePromptDialog";
import Tools from "./Tools";
import { PromptComponentProps } from "./types";
import { temporaryProviderEnum } from "./types";

const PROVIDER_TEXT = "Provider";
const PROMPT_NAME_TEXT = "Select Prompt";
const MODEL_TEXT = "Model";

const MODEL_OPTIONS = [
  { label: "Model 1", value: "model1" },
  { label: "Model 2", value: "model2" },
  { label: "Model 3", value: "model3" },
];

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt }: PromptComponentProps) => {
  const [nameInputValue, setNameInputValue] = useState("");
  const [currentPromptName, setCurrentPromptName] = useState<string>(
    prompt.name || ""
  );
  const [provider, setProvider] = useState<string>(
    temporaryProviderEnum.OPENAI
  );
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const [savePromptOpen, setSavePromptOpen] = useState<boolean>(false);

  const { state, dispatch } = usePromptContext();

  const handleSelectPrompt = useCallback(
    (event: SelectChangeEvent) => {
      const selection = event.target.value;
      if (selection === "") {
        return;
      }
      setCurrentPromptName(selection);

      const selectedPromptData = state.backendPrompts.find(
        (bp) => bp.name === selection
      );
      dispatch({
        type: "updatePrompt",
        payload: { promptId: prompt.id, prompt: selectedPromptData! },
      });
    },
    [prompt.id, state.backendPrompts, dispatch]
  );

  const handleProviderChange = (event: SelectChangeEvent) => {
    setProvider(event.target.value);
  };

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

  const handleAddMessage = useCallback(() => {
    dispatch({
      type: "addMessage",
      payload: { parentId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleParamsModelOpen = useCallback(() => {
    setParamsModelOpen(true);
  }, []);

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
        <div className="grid grid-cols-2 gap-1">
          <div className="flex justify-start items-center gap-1">
            <div className="w-1/3">
              <FormControl fullWidth variant="filled" size="small">
                <InputLabel id={`prompt-select-${prompt.id}`}>
                  {PROMPT_NAME_TEXT}
                </InputLabel>
                <Select
                  labelId={`prompt-select-${prompt.id}`}
                  id={`prompt-select-${prompt.id}`}
                  label={PROMPT_NAME_TEXT}
                  value={currentPromptName}
                  onChange={handleSelectPrompt}
                  sx={{
                    backgroundColor: "white",
                  }}
                >
                  <MenuItem value="">&nbsp;</MenuItem>
                  {currentPromptName &&
                    !state.backendPrompts.some(
                      (bp) => bp.name === currentPromptName
                    ) && (
                      <MenuItem
                        key={currentPromptName}
                        value={currentPromptName}
                      >
                        {currentPromptName}
                      </MenuItem>
                    )}
                  {state.backendPrompts.map((prompt) => (
                    <MenuItem key={prompt.name} value={prompt.name}>
                      {prompt.name}
                    </MenuItem>
                  ))}
                </Select>{" "}
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth variant="filled" size="small">
                <InputLabel id={`provider-${prompt.id}`}>
                  {PROVIDER_TEXT}
                </InputLabel>
                <Select
                  labelId={`provider-${prompt.id}`}
                  id={`provider-${prompt.id}`}
                  label={PROVIDER_TEXT}
                  value={provider}
                  onChange={handleProviderChange}
                  sx={{
                    backgroundColor: "white",
                  }}
                >
                  {Object.values(temporaryProviderEnum).map((providerValue) => (
                    <MenuItem key={providerValue} value={providerValue}>
                      {providerValue}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth variant="filled" size="small">
                <InputLabel id={`model-${prompt.id}`}>{MODEL_TEXT}</InputLabel>
                <Select
                  labelId={`model-${prompt.id}`}
                  id={`model-${prompt.id}`}
                  label={MODEL_TEXT}
                  value={MODEL_OPTIONS[0].value}
                  onChange={() => {}}
                  sx={{
                    backgroundColor: "white",
                  }}
                >
                  {MODEL_OPTIONS.map((modelOption) => (
                    <MenuItem key={modelOption.value} value={modelOption.value}>
                      {modelOption.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
          </div>
          <div className="flex justify-end items-center gap-1">
            <Tooltip title="Add Message" placement="top-start" arrow>
              <IconButton aria-label="add" onClick={handleAddMessage}>
                <AddIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Duplicate Prompt" placement="top-start" arrow>
              <IconButton
                aria-label="duplicate"
                onClick={handleDuplicatePrompt}
              >
                <ContentCopyIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Model Parameters" placement="top-start" arrow>
              <IconButton
                aria-label="model parameters"
                onClick={handleParamsModelOpen}
              >
                <SettingsIcon />
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
                <SaveIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete Prompt" placement="top-start" arrow>
              <IconButton aria-label="delete" onClick={handleDeletePrompt}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </div>
        </div>
      </Container>
      <div>
        {prompt.messages.map((message) => (
          <MessageComponent
            key={message.id}
            id={message.id}
            parentId={prompt.id}
            role={message.role}
            defaultContent={message.content}
            content={message.content}
          />
        ))}
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
