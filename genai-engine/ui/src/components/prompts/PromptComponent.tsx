import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import SettingsIcon from "@mui/icons-material/Settings";
import Autocomplete from "@mui/material/Autocomplete";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import MessagesSection from "./MessagesSection";
import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import { usePromptContext } from "./PromptContext";
import SavePromptDialog from "./SavePromptDialog";
import Tools from "./Tools";
import { PromptComponentProps } from "./types";

import { ModelProvider } from "@/lib/api-client/api-client";

const PROVIDER_TEXT = "Select Provider";
const PROMPT_NAME_TEXT = "Select Prompt";
const MODEL_TEXT = "Select Model";

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt }: PromptComponentProps) => {
  const [nameInputValue, setNameInputValue] = useState("");
  const [currentPromptName, setCurrentPromptName] = useState<string>(
    prompt.name || ""
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
    dispatch({
      type: "updatePromptProvider",
      payload: { promptId: prompt.id, provider: event.target.value },
    });
  };

  const handleModelChange = useCallback(
    (event: React.SyntheticEvent<Element, Event>, newValue: string | null) => {
      if (newValue === prompt.modelName) return;

      dispatch({
        type: "updatePromptModelName",
        payload: { promptId: prompt.id, modelName: newValue || "" },
      });
    },
    [dispatch, prompt.id, prompt.modelName]
  );

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

  const handleParamsModelOpen = useCallback(() => {
    setParamsModelOpen(true);
  }, []);

  useEffect(() => {
    setNameInputValue(currentPromptName);
  }, [currentPromptName]);

  useEffect(() => {
    if (state.enabledProviders.length > 0) {
      dispatch({
        type: "updatePromptProvider",
        payload: { promptId: prompt.id, provider: state.enabledProviders[0] },
      });
    }
  }, [state.enabledProviders, dispatch, prompt.id]);

  const providerDisabled = state.enabledProviders.length === 0;
  const modelDisabled = prompt.provider === "";
  const availableModels = useMemo(
    () => state.availableModels.get(prompt.provider as ModelProvider) || [],
    [state.availableModels, prompt.provider]
  );

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
                <Tooltip
                  title={
                    providerDisabled
                      ? "No providers available. Please configure at least one provider."
                      : ""
                  }
                  placement="top-start"
                  arrow
                >
                  <Select
                    labelId={`provider-${prompt.id}`}
                    id={`provider-${prompt.id}`}
                    label={PROVIDER_TEXT}
                    value={prompt.provider || ""}
                    onChange={handleProviderChange}
                    sx={{
                      backgroundColor: "white",
                    }}
                    disabled={providerDisabled}
                  >
                    <MenuItem value="">Select Provider</MenuItem>
                    {state.enabledProviders.map((provider) => (
                      <MenuItem key={provider} value={provider}>
                        {provider}
                      </MenuItem>
                    ))}
                  </Select>
                </Tooltip>
              </FormControl>
            </div>
            <div className="w-1/3">
              <Autocomplete
                id={`model-${prompt.id}`}
                options={availableModels}
                value={prompt.modelName || ""}
                onChange={handleModelChange}
                disabled={modelDisabled}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={MODEL_TEXT}
                    variant="filled"
                    size="small"
                    sx={{
                      backgroundColor: "white",
                    }}
                  />
                )}
              />
            </div>
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
