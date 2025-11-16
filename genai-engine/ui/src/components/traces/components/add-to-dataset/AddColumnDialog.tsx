import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Stack,
} from "@mui/material";
import { useState } from "react";
import { z } from "zod";

import { columnNameSchema } from "@/schemas/datasetSchemas";

interface AddColumnDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (columnName: string) => void;
  existingColumns: string[];
}

export const AddColumnDialog: React.FC<AddColumnDialogProps> = ({
  open,
  onClose,
  onSubmit,
  existingColumns,
}) => {
  const [columnName, setColumnName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const validateColumnName = (name: string): string | null => {
    try {
      columnNameSchema.parse(name);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return err.issues[0]?.message || "Invalid column name";
      }
    }

    if (existingColumns.includes(name.trim())) {
      return "Column name already exists";
    }

    return null;
  };

  const handleSubmit = () => {
    if (!columnName.trim()) {
      setError("Column name is required");
      return;
    }

    const validationError = validateColumnName(columnName);
    if (validationError) {
      setError(validationError);
      return;
    }

    onSubmit(columnName.trim());
    setColumnName("");
    setError(null);
  };

  const handleClose = () => {
    setColumnName("");
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add New Column</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label="Column Name"
            value={columnName}
            onChange={(e) => {
              setColumnName(e.target.value);
              setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="e.g., user_id, message, score"
            required
            fullWidth
            autoFocus
            error={!!error}
            helperText={error}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" disabled={!columnName.trim()}>
          Add Column
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddColumnDialog;
