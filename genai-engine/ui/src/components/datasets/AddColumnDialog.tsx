import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";
import React, { useState, useCallback } from "react";

interface AddColumnDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (columnName: string) => Promise<void>;
  existingColumns: string[];
  isLoading?: boolean;
}

export const AddColumnDialog: React.FC<AddColumnDialogProps> = ({
  open,
  onClose,
  onSubmit,
  existingColumns,
  isLoading = false,
}) => {
  const [columnName, setColumnName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const validateColumnName = useCallback(
    (name: string): string | null => {
      if (!name.trim()) {
        return "Column name is required";
      }
      if (existingColumns.includes(name.trim())) {
        return "Column name already exists";
      }
      if (name.length > 100) {
        return "Column name must be less than 100 characters";
      }
      return null;
    },
    [existingColumns]
  );

  const handleSubmit = useCallback(async () => {
    const validationError = validateColumnName(columnName);
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      await onSubmit(columnName.trim());
      setColumnName("");
      setError(null);
    } catch (err) {
      console.error("Failed to add column:", err);
      setError("Failed to add column. Please try again.");
    }
  }, [columnName, onSubmit, validateColumnName]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      setColumnName("");
      setError(null);
      onClose();
    }
  }, [isLoading, onClose]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      aria-labelledby="add-column-dialog-title"
    >
      <DialogTitle id="add-column-dialog-title">Add Column</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          label="Column Name"
          type="text"
          fullWidth
          variant="outlined"
          value={columnName}
          onChange={(e) => {
            setColumnName(e.target.value);
            setError(null);
          }}
          error={!!error}
          helperText={error}
          disabled={isLoading}
          onKeyDown={handleKeyDown}
          placeholder="e.g., user_id, message, score"
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isLoading} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isLoading || !columnName.trim()}
          variant="contained"
          color="primary"
          startIcon={isLoading ? <CircularProgress size={16} /> : null}
        >
          {isLoading ? "Adding..." : "Add Column"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
