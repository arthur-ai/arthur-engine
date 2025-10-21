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
import { useForm } from "@tanstack/react-form";
import React, { useMemo } from "react";

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
  const columns = Object.keys(rowData);

  const stringData = useMemo(() => {
    const data: Record<string, string> = {};
    Object.entries(rowData).forEach(([key, value]) => {
      data[key] = String(value ?? "");
    });
    return data;
  }, [rowData]);

  const form = useForm({
    defaultValues: stringData,
    onSubmit: async ({ value }) => {
      await onSubmit(value);
    },
  });

  const handleClose = () => {
    if (!isLoading) {
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="edit-row-dialog-title"
    >
      <form
        key={rowId}
        onSubmit={(e) => {
          e.preventDefault();
          form.handleSubmit();
        }}
      >
        <DialogTitle id="edit-row-dialog-title">
          {rowId === "new" ? "Add Row" : "Edit Row"}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
            {columns.map((column) => (
              <form.Field key={column} name={column}>
                {(field) => {
                  const value = field.state.value;
                  return (
                    <TextField
                      label={column}
                      value={value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      disabled={isLoading}
                      fullWidth
                      size="small"
                      multiline={value.length > 50}
                      rows={value.length > 50 ? 3 : 1}
                    />
                  );
                }}
              </form.Field>
            ))}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={isLoading} color="inherit">
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isLoading}
            variant="contained"
            color="primary"
            startIcon={isLoading ? <CircularProgress size={16} /> : null}
          >
            {isLoading ? "Saving..." : "Save"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};
