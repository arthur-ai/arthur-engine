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

import { SavePromptDialogProps } from "./types";
import { toBackendPromptBaseConfig } from "./utils";

import { SNACKBAR_AUTO_HIDE_DURATION } from "@/constants/snackbar";
import { useApi } from "@/hooks/useApi";
import useSnackbar from "@/hooks/useSnackbar";
import { useTask } from "@/hooks/useTask";
import { AgenticPrompt } from "@/lib/api-client/api-client";

const SavePromptDialog = ({
  open,
  setOpen,
  prompt,
  initialName = "",
  onSaveSuccess,
  onSaveError,
}: SavePromptDialogProps) => {
  const [nameInputValue, setNameInputValue] = useState("");
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

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

  const handleSavePrompt = useCallback(() => {
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

    apiClient.api
      .saveAgenticPromptApiV1TasksTaskIdPromptsPromptNamePost(
        nameInputValue,
        taskId,
        backendPrompt
      )
      .then((response: { data: AgenticPrompt }) => {
        const { data } = response;
        showSnackbar(`Saved prompt: ${data.name}`, "success");
        onSaveSuccess?.();
        handleClose();
      })
      .catch((error: { response: { data: { detail: string } } }) => {
        const { data } = error.response;
        showSnackbar(data.detail, "error");
        onSaveError?.(data.detail);
      });
  }, [
    nameInputValue,
    prompt,
    apiClient,
    taskId,
    showSnackbar,
    onSaveSuccess,
    onSaveError,
    handleClose,
  ]);

  return (
    <>
      <Dialog open={open} onClose={handleClose} fullWidth>
        <DialogTitle>Save Prompt</DialogTitle>
        <DialogContent>
          <DialogContentText className="text-center">
            Saving a prompt with an existing name will create a new version of
            the prompt.
          </DialogContentText>
          <div className="p-2">
            <TextField
              label="Prompt Name"
              value={nameInputValue}
              onChange={(event) => setNameInputValue(event.target.value)}
              fullWidth
              autoFocus
            />
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
