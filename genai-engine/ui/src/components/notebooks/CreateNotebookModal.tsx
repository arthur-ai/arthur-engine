import {
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from "@mui/material";
import { useForm } from "@tanstack/react-form";
import React from "react";

import type { CreateNotebookRequest } from "@/lib/api-client/api-client";

interface CreateNotebookModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CreateNotebookRequest) => Promise<void>;
  isLoading?: boolean;
}

interface CreateNotebookFormContentProps {
  onClose: () => void;
  onSubmit: (data: CreateNotebookRequest) => Promise<void>;
  isLoading: boolean;
}

const CreateNotebookFormContent: React.FC<CreateNotebookFormContentProps> = ({
  onClose,
  onSubmit,
  isLoading,
}) => {
  const form = useForm({
    defaultValues: {
      name: "",
      description: "",
    },
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
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          form.handleSubmit();
        }}
      >
        <DialogTitle id="create-notebook-dialog-title">Create Notebook</DialogTitle>
        <DialogContent>
          <form.Field
            name="name"
            validators={{
              onChange: ({ value }) =>
                !value || value.trim().length === 0
                  ? "Notebook name is required"
                  : value.length > 100
                  ? "Notebook name must be less than 100 characters"
                  : undefined,
            }}
          >
            {(field) => (
              <TextField
                autoFocus
                margin="dense"
                label="Notebook Name"
                type="text"
                fullWidth
                variant="outlined"
                required
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0]}
                disabled={isLoading}
                sx={{ mt: 2 }}
              />
            )}
          </form.Field>

          <form.Field
            name="description"
            validators={{
              onChange: ({ value }) =>
                value && value.length > 500
                  ? "Description must be less than 500 characters"
                  : undefined,
            }}
          >
            {(field) => (
              <TextField
                margin="dense"
                label="Description (Optional)"
                type="text"
                fullWidth
                variant="outlined"
                multiline
                rows={3}
                value={field.state.value || ""}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                error={field.state.meta.errors.length > 0}
                helperText={field.state.meta.errors[0]}
                disabled={isLoading}
                sx={{ mt: 2 }}
              />
            )}
          </form.Field>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleClose} disabled={isLoading} color="inherit">
            Cancel
          </Button>
          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting]}
          >
            {([canSubmit]) => (
              <Button
                type="submit"
                disabled={!canSubmit || isLoading}
                variant="contained"
                color="primary"
                startIcon={isLoading ? <CircularProgress size={16} /> : null}
              >
                {isLoading ? "Creating..." : "Create"}
              </Button>
            )}
          </form.Subscribe>
        </DialogActions>
      </form>
    </>
  );
};

export const CreateNotebookModal: React.FC<CreateNotebookModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading = false,
}) => {
  return (
    <Dialog
      open={open}
      onClose={() => {
        if (!isLoading) {
          onClose();
        }
      }}
      maxWidth="sm"
      fullWidth
      aria-labelledby="create-notebook-dialog-title"
    >
      <CreateNotebookFormContent
        key="create-notebook"
        onClose={onClose}
        onSubmit={onSubmit}
        isLoading={isLoading}
      />
    </Dialog>
  );
};
