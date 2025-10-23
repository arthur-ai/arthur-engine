import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import SettingsIcon from "@mui/icons-material/Settings";
import Alert from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import React, {
  SyntheticEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import MessagesSection from "./MessagesSection";
import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import { usePromptContext } from "./PromptsPlaygroundContext";
import SavePromptDialog from "./SavePromptDialog";
import Tools from "./Tools";
import { PromptComponentProps } from "./types";

import useSnackbar from "@/hooks/useSnackbar";
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
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const handleSelectPrompt = (
    _event: SyntheticEvent<Element, Event>,
    newValue: string | null
  ) => {
    const selection = newValue || "";
    if (selection === "") {
      return;
    }
    setCurrentPromptName(selection);

    const backendPromptData = state.backendPrompts.find(
      (bp) => bp.name === selection
    );

    if (typeof backendPromptData === "undefined") {
      showSnackbar("Prompt not found", "error");
      return;
    }

    // dispatch({
    //   type: "updatePrompt",
    //   payload: { promptId: prompt.id, prompt: backendPromptData },
    // });
  };

  const handleProviderChange = (
    _event: SyntheticEvent<Element, Event>,
    newValue: string | null
  ) => {
    dispatch({
      type: "updatePromptProvider",
      payload: { promptId: prompt.id, provider: newValue || "" },
    });
  };

  const handleModelChange = (
    _event: SyntheticEvent<Element, Event>,
    newValue: string | null
  ) => {
    dispatch({
      type: "updatePromptModelName",
      payload: { promptId: prompt.id, modelName: newValue || "" },
    });
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

  const handleParamsModelOpen = () => {
    setParamsModelOpen(true);
  };

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
  const backendPromptOptions = state.backendPrompts.map(
    (backendPrompt) => backendPrompt.name
  );
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
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-1">
          <div className="flex justify-start items-center gap-1">
            <div className="w-1/3">
              <Autocomplete
                id={`prompt-select-${prompt.id}`}
                options={backendPromptOptions}
                value={currentPromptName}
                onChange={handleSelectPrompt}
                disabled={state.backendPrompts.length === 0}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={PROMPT_NAME_TEXT}
                    variant="standard"
                    sx={{
                      backgroundColor: "white",
                    }}
                  />
                )}
              />
            </div>
            <div className="w-1/3">
              <Tooltip
                title={
                  providerDisabled
                    ? "No providers available. Please configure at least one provider."
                    : ""
                }
                placement="top-start"
                arrow
              >
                <Autocomplete
                  id={`provider-${prompt.id}`}
                  options={state.enabledProviders}
                  value={prompt.provider || ""}
                  onChange={handleProviderChange}
                  disabled={providerDisabled}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label={PROVIDER_TEXT}
                      variant="standard"
                      sx={{
                        backgroundColor: "white",
                      }}
                    />
                  )}
                />
              </Tooltip>
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
                    variant="standard"
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
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </div>
  );
};

export default Prompt;
