import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, TextField, Typography } from "@mui/material";
import React, { useState } from "react";

interface FillColumnModalProps {
  open: boolean;
  columnName: string;
  totalRowCount: number;
  onClose: () => void;
  onApply: (value: string) => void;
  isLoading: boolean;
}

export const FillColumnModal: React.FC<FillColumnModalProps> = ({ open, columnName, totalRowCount, onClose, onApply, isLoading }) => {
  const [value, setValue] = useState("");

  const handleClose = () => {
    if (!isLoading) {
      setValue("");
      onClose();
    }
  };

  const handleApply = () => {
    onApply(value);
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth aria-labelledby="fill-column-dialog-title">
      <DialogTitle id="fill-column-dialog-title">Fill Column: {columnName}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            autoFocus
            label="Value to apply to all rows"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={isLoading}
            fullWidth
            multiline
            minRows={2}
            maxRows={6}
            placeholder="Enter the value to set for all rows..."
          />
          <Alert severity="warning" icon={<WarningAmberIcon fontSize="inherit" />} sx={{ mt: 1 }}>
            <Typography variant="body2">
              This will update all <strong>{totalRowCount}</strong> row
              {totalRowCount !== 1 ? "s" : ""} and create a new dataset version.
            </Typography>
          </Alert>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} color="inherit" disabled={isLoading}>
          Cancel
        </Button>
        <Button
          onClick={handleApply}
          variant="contained"
          color="primary"
          disabled={isLoading}
          startIcon={isLoading ? <CircularProgress size={16} /> : undefined}
        >
          {isLoading ? "Applying..." : "Apply & Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
