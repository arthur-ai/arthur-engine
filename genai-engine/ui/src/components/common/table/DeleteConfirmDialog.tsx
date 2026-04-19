import { Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle } from "@mui/material";
import React from "react";

interface DeleteConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  /** Primary confirmation message. Supports ReactNode for bold item names. */
  description: React.ReactNode;
  /**
   * Optional warning text shown in a yellow highlighted box.
   * Use for destructive/irreversible cascading deletes.
   */
  warningText?: string;
  /**
   * Optional note text shown in a blue info box.
   * Use for informational side-effects (e.g. related records will be preserved).
   */
  noteText?: string;
  isDeleting?: boolean;
}

/**
 * Standard delete confirmation dialog used by all tables.
 * Replaces per-table duplicate implementations across Datasets, Evals,
 * Prompts, Transforms, and Agent Notebooks.
 */
export const DeleteConfirmDialog: React.FC<DeleteConfirmDialogProps> = ({
  open,
  onClose,
  onConfirm,
  title,
  description,
  warningText,
  noteText,
  isDeleting = false,
}) => {
  return (
    <Dialog open={open} onClose={onClose} aria-labelledby="delete-dialog-title" aria-describedby="delete-dialog-description">
      <DialogTitle id="delete-dialog-title">{title}</DialogTitle>
      <DialogContent>
        <DialogContentText id="delete-dialog-description">{description}</DialogContentText>
        {warningText && (
          <Box sx={{ mt: 2, p: 2, bgcolor: "warning.lighter", borderRadius: 1 }}>
            <strong>Warning:</strong> {warningText}
          </Box>
        )}
        {noteText && (
          <Box sx={{ mt: 2, p: 2, bgcolor: "info.lighter", borderRadius: 1 }}>
            <strong>Note:</strong> {noteText}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={isDeleting}>
          Cancel
        </Button>
        <Button
          onClick={onConfirm}
          color="error"
          variant="contained"
          disabled={isDeleting}
          startIcon={isDeleting ? <CircularProgress size={16} /> : null}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
