import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";
import React, { useState, useCallback, useEffect } from "react";

interface EditRowModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (rowData: Record<string, unknown>) => Promise<void>;
  rowData: Record<string, unknown>;
  rowId: string;
  isLoading?: boolean;
}

export const EditRowModal: React.FC<EditRowModalProps> = ({
  open,
  onClose,
  onSubmit,
  rowData,
  rowId,
  isLoading = false,
}) => {
  const [editedData, setEditedData] = useState<Record<string, string>>({});

  // Initialize edited data when modal opens or rowData changes
  useEffect(() => {
    if (open) {
      const stringData: Record<string, string> = {};
      Object.entries(rowData).forEach(([key, value]) => {
        stringData[key] = String(value ?? "");
      });
      setEditedData(stringData);
    }
  }, [open, rowData]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      onClose();
    }
  }, [isLoading, onClose]);

  const handleFieldChange = useCallback((key: string, value: string) => {
    setEditedData((prev) => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  const handleSubmit = useCallback(async () => {
    try {
      await onSubmit(editedData);
    } catch (err) {
      console.error("Failed to submit row:", err);
    }
  }, [editedData, onSubmit]);

  const columns = Object.keys(rowData);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="edit-row-dialog-title"
    >
      <DialogTitle id="edit-row-dialog-title">
        {rowId === "new" ? "Add Row" : `Edit Row: ${rowId}`}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {columns.map((column) => {
            const value = editedData[column] ?? "";

            return (
              <TextField
                key={column}
                label={column}
                value={value}
                onChange={(e) => handleFieldChange(column, e.target.value)}
                disabled={isLoading}
                fullWidth
                size="small"
                multiline={value.length > 50}
                rows={value.length > 50 ? 3 : 1}
              />
            );
          })}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isLoading} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isLoading}
          variant="contained"
          color="primary"
          startIcon={isLoading ? <CircularProgress size={16} /> : null}
        >
          {isLoading ? "Saving..." : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
