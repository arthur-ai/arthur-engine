import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import React, { useCallback, useEffect, useState } from "react";

import MessagesSection from "../messages/MessagesSection";
import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptComponentProps } from "../types";
import { toCompletionRequest } from "../utils";

import ManagementButtons from "./ManagementButtons";
import OutputField from "./OutputField";
import PromptSelectors from "./PromptSelectors";
import SavePromptDialog from "./SavePromptDialog";
import ToolsDialog from "./ToolsDialog";

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
  const [savePromptOpen, setSavePromptOpen] = useState<boolean>(false);
  const [toolsDialogOpen, setToolsDialogOpen] = useState<boolean>(false);
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

  useEffect(() => {
    setNameInputValue(currentPromptName);
  }, [currentPromptName]);

  useEffect(() => {
    if (prompt.running) {
      runPrompt();
    }
  }, [prompt.running, runPrompt]);

  return (
    <div className="h-full shadow-md rounded-lg p-1 bg-gray-200 flex flex-col">
      <Container component="div" className="p-1 mt-1 flex flex-col h-full" maxWidth="lg" disableGutters>
        <div className="flex justify-between items-center gap-1">
          <div className="flex justify-start items-center">
            {prompt.tools.length > 0 ? (
              <Badge badgeContent={prompt.tools.length} color="primary">
                <Button variant="outlined" size="small" onClick={() => setToolsDialogOpen(true)}>
                  Tools
                </Button>
              </Badge>
            ) : (
              <Button variant="outlined" size="small" onClick={() => setToolsDialogOpen(true)}>
                Tools
              </Button>
            )}
          </div>
          <div className="flex justify-end items-center gap-1 flex-shrink-0">
            <ManagementButtons prompt={prompt} setSavePromptOpen={setSavePromptOpen} />
          </div>
        </div>
        <div className="min-w-[300px] flex-shrink-0">
          <PromptSelectors prompt={prompt} currentPromptName={currentPromptName} onPromptNameChange={setCurrentPromptName} />
        </div>
        <div className="mt-1 flex-1 min-h-0">
          <Paper elevation={2} className="p-1 h-full">
            <MessagesSection prompt={prompt} />
          </Paper>
        </div>
        <div className="mt-1 flex-shrink-0" style={{ minHeight: "30%" }}>
          <Paper elevation={2} className="p-1 h-full">
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
      <ToolsDialog open={toolsDialogOpen} setOpen={setToolsDialogOpen} prompt={prompt} />
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </div>
  );
};

export default Prompt;
