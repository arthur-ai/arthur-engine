import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import SettingsIcon from "@mui/icons-material/Settings";
import Alert, { AlertColor } from "@mui/material/Alert";
import Autocomplete from "@mui/material/Autocomplete";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import { debounce } from "@mui/material/utils";
import React, { useCallback, useEffect, useMemo, useState } from "react";

import MessageComponent from "./MessageComponent";
import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import { usePromptContext } from "./PromptContext";
import Tools from "./Tools";
import { PromptComponentProps } from "./types";
import { providerEnum } from "./types";
import { toBackendPrompt } from "./utils";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

const PROVIDER_TEXT = "Provider";
const PROMPT_NAME_TEXT = "Prompt Name";
const MODEL_TEXT = "Model";
const DEBOUNCE_TIME = 500;
const SNACKBAR_AUTO_HIDE_DURATION = 6000;

const MODEL_OPTIONS = [
  { label: "Model 1", value: "model1" },
  { label: "Model 2", value: "model2" },
  { label: "Model 3", value: "model3" },
];

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt }: PromptComponentProps) => {
  const [NameInputValue, setNameInputValue] = useState("");
  const [provider, setProvider] = useState<string>(providerEnum.OPENAI);
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const [openSnackbar, setOpenSnackbar] = useState<boolean>(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string>("");
  const [snackbarSeverity, setSnackbarSeverity] =
    useState<AlertColor>("success");

  const { state, dispatch } = usePromptContext();
  const apiClient = useApi();
  const { task } = useTask();
  const api = apiClient?.v1; // Prompt endpoints live here
  const taskId = task?.id;

  const handleProviderChange = (event: SelectChangeEvent) => {
    setProvider(event.target.value);
  };

  const handleSavePrompt = useCallback(() => {
    if (prompt.name === "") {
      return;
    }
    if (!api || !taskId) {
      console.error("No api client or task");
      return;
    }

    const backendPrompt = toBackendPrompt(prompt);

    api
      .saveAgenticPromptV1TaskIdAgenticPromptSavePromptPost(
        taskId,
        backendPrompt
      )
      .then((response) => {
        // {message: "Prompt saved successfully"}
        const { data } = response;
        setSnackbarMessage(data.message);
        setSnackbarSeverity("success");
        setOpenSnackbar(true);
      })
      .catch((error) => {
        // {detail: "Prompt ... already exists for task ..."}
        const { data } = error.response;
        setSnackbarMessage(data.detail);
        setSnackbarSeverity("error");
        setOpenSnackbar(true);
      });
  }, [prompt, api, taskId]);

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

  const handleCloseSnackbar = useCallback(() => {
    setOpenSnackbar(false);
    setSnackbarMessage("");
  }, []);

  const debouncedSetPromptName = useMemo(
    () =>
      debounce((value: string) => {
        if (value === prompt.name) return;
        dispatch({
          type: "updatePromptName",
          payload: { promptId: prompt.id, name: value },
        });
      }, DEBOUNCE_TIME),
    [prompt.name, prompt.id, dispatch]
  );

  useEffect(() => {
    debouncedSetPromptName(NameInputValue);
  }, [NameInputValue, debouncedSetPromptName]);

  return (
    <div className="min-h-[500px]">
      <Container
        component="div"
        className="p-1 mt-1"
        maxWidth="xl"
        disableGutters
      >
        <div className="grid grid-cols-2 gap-1">
          <div className="flex justify-start items-center gap-1">
            <div className="w-1/3">
              <Autocomplete
                freeSolo
                options={state.backendPrompts.map((prompt) => prompt.name)}
                value={prompt.name}
                renderInput={(params) => (
                  <TextField {...params} label={PROMPT_NAME_TEXT} />
                )}
                inputValue={NameInputValue}
                onInputChange={(event, value) => {
                  setNameInputValue(value);
                }}
                sx={{
                  backgroundColor: "white",
                }}
              />
            </div>
            <div className="w-1/3">
              <FormControl fullWidth variant="filled">
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
                  {Object.values(providerEnum).map((providerValue) => (
                    <MenuItem key={providerValue} value={providerValue}>
                      {providerValue}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth variant="filled">
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
              <IconButton aria-label="save" onClick={handleSavePrompt}>
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
      <Snackbar
        open={openSnackbar}
        autoHideDuration={SNACKBAR_AUTO_HIDE_DURATION}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
      >
        <Alert severity={snackbarSeverity}>{snackbarMessage}</Alert>
      </Snackbar>
    </div>
  );
};

export default Prompt;
