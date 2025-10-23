import Alert, { AlertColor } from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Snackbar from "@mui/material/Snackbar";
import TextField from "@mui/material/TextField";
import React, { useCallback, useEffect, useState } from "react";

import { SavePromptDialogProps } from "./types";
import { toBackendPromptBaseConfig } from "./utils";

import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";

const SNACKBAR_AUTO_HIDE_DURATION = 6000;

const SavePromptDialog = ({
  open,
  setOpen,
  prompt,
  initialName = "",
  onSaveSuccess,
  onSaveError,
}: SavePromptDialogProps) => {
  const [nameInputValue, setNameInputValue] = useState("");
  const [openSnackbar, setOpenSnackbar] = useState<boolean>(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string>("");
  const [snackbarSeverity, setSnackbarSeverity] =
    useState<AlertColor>("success");

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
      setSnackbarMessage("Prompt name is required");
      setSnackbarSeverity("error");
      setOpenSnackbar(true);
      return;
    }

    if (!apiClient || !taskId) {
      console.error("No api client or task");
      setSnackbarMessage("API Error");
      setSnackbarSeverity("error");
      setOpenSnackbar(true);
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
      .then((response: { data: { message: string } }) => {
        const { data } = response;
        setSnackbarMessage(data.message);
        setSnackbarSeverity("success");
        setOpenSnackbar(true);
        onSaveSuccess?.();
        handleClose();
      })
      .catch((error: { response: { data: { detail: string } } }) => {
        const { data } = error.response;
        setSnackbarMessage(data.detail);
        setSnackbarSeverity("error");
        setOpenSnackbar(true);
        onSaveError?.(data.detail);
      });
  }, [
    nameInputValue,
    prompt,
    apiClient,
    taskId,
    onSaveSuccess,
    onSaveError,
    handleClose,
  ]);

  const handleCloseSnackbar = useCallback(() => {
    setOpenSnackbar(false);
    setSnackbarMessage("");
  }, []);

  return (
    <>
      <Dialog open={open} onClose={handleClose} fullWidth>
        <DialogTitle>Save Prompt</DialogTitle>
        <DialogContent>
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

      <Snackbar
        open={openSnackbar}
        autoHideDuration={SNACKBAR_AUTO_HIDE_DURATION}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
      >
        <Alert severity={snackbarSeverity}>{snackbarMessage}</Alert>
      </Snackbar>
    </>
  );
};

export default SavePromptDialog;
