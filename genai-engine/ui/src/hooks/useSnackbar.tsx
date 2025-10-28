import { AlertColor, AlertProps } from "@mui/material/Alert";
import { SnackbarProps } from "@mui/material/Snackbar";
import { useCallback, useState } from "react";

const SNACKBAR_AUTO_HIDE_DURATION = 6000;

const useSnackbar = () => {
  const [openSnackbar, setOpenSnackbar] = useState<boolean>(false);
  const [snackbarMessage, setSnackbarMessage] = useState<string>("");
  const [snackbarSeverity, setSnackbarSeverity] =
    useState<AlertColor>("success");

  const showSnackbar = useCallback(
    (message: string, severity: AlertColor = "success") => {
      setSnackbarMessage(message);
      setSnackbarSeverity(severity);
      setOpenSnackbar(true);
    },
    []
  );

  const hideSnackbar = () => {
    setOpenSnackbar(false);
  };

  const snackbarProps: SnackbarProps = {
    open: openSnackbar,
    anchorOrigin: { vertical: "top", horizontal: "center" },
    autoHideDuration: SNACKBAR_AUTO_HIDE_DURATION,
    onClose: hideSnackbar,
  };

  const alertProps: AlertProps = {
    severity: snackbarSeverity,
    children: snackbarMessage,
  };

  return {
    showSnackbar,
    hideSnackbar,
    snackbarProps,
    alertProps,
  };
};

export default useSnackbar;
