import { AlertColor, AlertProps } from "@mui/material/Alert";
import { SnackbarProps } from "@mui/material/Snackbar";
import { useCallback, useState } from "react";

type SnackbarDuration = "short" | "default";

interface UseSnackbarOptions {
  duration?: SnackbarDuration;
}

const DURATION_MAP: Record<SnackbarDuration, number> = {
  short: 2000,
  default: 6000,
};

const useSnackbar = (options?: UseSnackbarOptions) => {
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

  const duration = DURATION_MAP[options?.duration ?? "default"];

  const snackbarProps: SnackbarProps = {
    open: openSnackbar,
    anchorOrigin: { vertical: "top", horizontal: "center" },
    autoHideDuration: duration,
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
