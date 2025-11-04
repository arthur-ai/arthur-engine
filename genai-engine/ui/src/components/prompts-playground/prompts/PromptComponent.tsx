import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
// import SettingsIcon from "@mui/icons-material/Settings"; Use for permanent delete option
import TuneIcon from "@mui/icons-material/Tune";
import Alert from "@mui/material/Alert";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useEffect, useState } from "react";

import MessagesSection from "../messages/MessagesSection";
import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptComponentProps } from "../types";
import { toCompletionRequest } from "../utils";

import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import PromptSelectors from "./PromptSelectors";
import SavePromptDialog from "./SavePromptDialog";
import Tools from "./Tools";

import { useApi } from "@/hooks/useApi";
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt }: PromptComponentProps) => {
  // This name value updates when an existing prompt is selected
  const [currentPromptName, setCurrentPromptName] = useState<string>(prompt.name || "");
  const [nameInputValue, setNameInputValue] = useState("");
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const [savePromptOpen, setSavePromptOpen] = useState<boolean>(false);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const { state, dispatch } = usePromptContext();
  const apiClient = useApi();
  const { task } = useTask();
  const taskId = task?.id;

  const runPrompt = useCallback(async () => {
    if (!apiClient || !taskId) {
      console.error("No api client or task id");
      return;
    }
    // Replace template strings with variable values before sending to API
    const completionRequest = toCompletionRequest(prompt, state.keywords);
    await apiClient.api
      .runAgenticPromptApiV1CompletionsPost(completionRequest)
      .then((response) => {
        dispatch({
          type: "updatePrompt",
          payload: {
            promptId: prompt.id,
            prompt: { running: false, runResponse: response.data },
          },
        });
      })
      .catch((error) => {
        console.error("Error running prompt:", error);
        showSnackbar(error.response.data.detail, "error");
        dispatch({
          type: "updatePrompt",
          payload: {
            promptId: prompt.id,
            prompt: { running: false, runResponse: null },
          },
        });
      });
  }, [apiClient, taskId, prompt, state.keywords, dispatch, showSnackbar]);

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

  const handleRunPrompt = useCallback(() => {
    dispatch({
      type: "runPrompt",
      payload: { promptId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleParamsModelOpen = () => {
    setParamsModelOpen(true);
  };

  useEffect(() => {
    setNameInputValue(currentPromptName);
  }, [currentPromptName]);

  useEffect(() => {
    if (prompt.running) {
      runPrompt();
    }
  }, [prompt.running, runPrompt]);

  const runDisabled = prompt.running || prompt.modelName === "";
  return (
    <div className="min-h-[500px] shadow-md rounded-lg p-4">
      <Container component="div" className="p-1 mt-1" maxWidth="xl" disableGutters>
        <div className="flex flex-wrap items-center gap-1">
          <div className="flex-1 min-w-[300px]">
            <PromptSelectors prompt={prompt} currentPromptName={currentPromptName} onPromptNameChange={setCurrentPromptName} />
          </div>
          <div className="flex justify-end items-center gap-1 flex-shrink-0">
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
        <div className="mt-1">
          <Paper elevation={2} className="p-1">
            <MessagesSection prompt={prompt} />
          </Paper>
        </div>
        <div className="mt-1">
          <Paper elevation={2} className="p-1">
            <Tools prompt={prompt} />
          </Paper>
        </div>
        <div className="mt-1">
          <Paper elevation={2} className="p-1">
            <OutputField
              promptId={prompt.id}
              running={prompt.running || false}
              runResponse={prompt.runResponse}
              responseFormat={prompt.responseFormat}
            />
          </Paper>
        </div>
      </Container>
      <SavePromptDialog open={savePromptOpen} setOpen={setSavePromptOpen} prompt={prompt} initialName={nameInputValue} />
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </div>
  );
};

export default Prompt;
