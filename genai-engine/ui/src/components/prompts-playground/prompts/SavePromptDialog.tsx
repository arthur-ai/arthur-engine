import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import React, { useCallback, useEffect, useState } from "react";

import { useFetchBackendPrompts } from "../hooks/useFetchBackendPrompts";
import { usePromptContext } from "../PromptsPlaygroundContext";
import { SavePromptDialogProps } from "../types";
import { toBackendPromptBaseConfig } from "../utils/toBackendPrompt";

import { useApi } from "@/hooks/useApi";
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";
import { AgenticPrompt } from "@/lib/api-client/api-client";

const SavePromptDialog = ({ open, setOpen, prompt, initialName = "" }: SavePromptDialogProps) => {
  const [nameInputValue, setNameInputValue] = useState("");
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();
  const { dispatch } = usePromptContext();
  const fetchPrompts = useFetchBackendPrompts();

  const apiClient = useApi();
  const { task } = useTask();
  const taskId = task?.id;

  // Update name input when initialName changes
  useEffect(() => {
    setNameInputValue(initialName);
  }, [initialName]);

  const handleClose = useCallback(() => {
    setOpen(false);
  }, [setOpen]);

  const handleSavePrompt = useCallback(async () => {
    if (nameInputValue === "") {
      showSnackbar("Prompt name is required", "error");
      return;
    }

    if (!apiClient || !taskId) {
      console.error("No api client or task");
      showSnackbar("API Error", "error");
      return;
    }

    // We remove the name because the endpoint signature expects it as a standalone parameter
    const backendPrompt = toBackendPromptBaseConfig(prompt);

    try {
      const response: { data: AgenticPrompt } = await apiClient.api.saveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePost(
        nameInputValue,
        taskId,
        backendPrompt
      );
      const { data } = response;
      showSnackbar(`Saved prompt: ${data.name}`, "success");
      handleClose();
      fetchPrompts(dispatch);
      // Update name, version, and clear dirty flag after saving
      dispatch({
        type: "updatePrompt",
        payload: {
          promptId: prompt.id,
          prompt: {
            name: nameInputValue,
            version: data.version,
            isDirty: false,
          },
        },
      });
    } catch (error: unknown) {
      const apiError = error as { response: { data: { detail: string } } };
      if (apiError?.response?.data?.detail) {
        showSnackbar(apiError.response.data.detail, "error");
      } else {
        showSnackbar("Failed to save prompt", "error");
      }
    }
  }, [nameInputValue, prompt, apiClient, taskId, showSnackbar, handleClose, fetchPrompts, dispatch]);

  return (
    <>
      <Dialog open={open} onClose={handleClose} fullWidth>
        <DialogTitle>Save Prompt</DialogTitle>
        <DialogContent>
          <DialogContentText className="text-center">
            Saving a prompt with an existing name will create a new version of the prompt.
          </DialogContentText>
          <div className="p-2">
            <TextField label="Prompt Name" value={nameInputValue} onChange={(event) => setNameInputValue(event.target.value)} fullWidth autoFocus />
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSavePrompt} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};

export default SavePromptDialog;
