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
import React, { useState } from "react";

import { SNACKBAR_SHORT_AUTO_HIDE_DURATION } from "@/constants/snackbar";
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
  const [showCopySuccess, setShowCopySuccess] = useState(false);

  const fullValue = formatFullValue(value);
  const charCount = fullValue.length;

  const handleCopy = () => {
    navigator.clipboard.writeText(fullValue);
    setShowCopySuccess(true);
  };

  const handleClose = () => {
    setShowCopySuccess(false);
    onClose();
  };

  return (
    <>
      <Dialog
        open={open}
        onClose={handleClose}
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
              bgcolor: "grey.50",
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
          <Button onClick={handleClose} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>

      <Portal>
        <Snackbar
          open={showCopySuccess}
          autoHideDuration={SNACKBAR_SHORT_AUTO_HIDE_DURATION}
          onClose={() => setShowCopySuccess(false)}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        >
          <Alert
            onClose={() => setShowCopySuccess(false)}
            severity="success"
            sx={{ width: "100%" }}
          >
            Copied to clipboard!
          </Alert>
        </Snackbar>
      </Portal>
    </>
  );
};
