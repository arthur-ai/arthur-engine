import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Portal,
  Snackbar,
  Typography,
} from "@mui/material";
import React from "react";

import useSnackbar from "@/hooks/useSnackbar";
import { formatFullValue } from "@/utils/datasetFormatters";

interface CellContentModalProps {
  open: boolean;
  onClose: () => void;
  columnName: string;
  value: unknown;
}

export const CellContentModal: React.FC<CellContentModalProps> = ({
  open,
  onClose,
  columnName,
  value,
}) => {
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar({
    duration: "short",
  });

  const fullValue = formatFullValue(value);
  const charCount = fullValue.length;

  const handleCopy = () => {
    navigator.clipboard.writeText(fullValue);
    showSnackbar("Copied to clipboard!", "success");
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={onClose}
        maxWidth="md"
        fullWidth
        onClick={(e) => e.stopPropagation()}
      >
        <DialogTitle>
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 2,
            }}
          >
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" gutterBottom>
                {columnName}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {charCount.toLocaleString()} characters
              </Typography>
            </Box>
            <IconButton
              size="small"
              onClick={handleCopy}
              title="Copy to clipboard"
              sx={{
                "&:hover": { color: "primary.main" },
                flexShrink: 0,
              }}
            >
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          <Box
            sx={{
              p: 2,
              bgcolor: "background.default",
              borderRadius: 1,
              fontSize: "0.875rem",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              minHeight: "200px",
              maxHeight: "60vh",
              overflow: "auto",
              border: 1,
              borderColor: "divider",
              lineHeight: 1.6,
            }}
          >
            {fullValue}
          </Box>
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleCopy} variant="outlined" size="small">
            Copy
          </Button>
          <Button onClick={onClose} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      <Portal>
        <Snackbar {...snackbarProps}>
          <Alert {...alertProps} />
        </Snackbar>
      </Portal>
    </>
  );
};
