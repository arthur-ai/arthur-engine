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

import { DatasetFormData } from "@/types/dataset";

interface DatasetFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: DatasetFormData) => Promise<void>;
  isLoading?: boolean;
  mode: "create" | "edit";
  initialData?: DatasetFormData;
  datasetId?: string;
}

interface DatasetFormContentProps {
  onClose: () => void;
  onSubmit: (data: DatasetFormData) => Promise<void>;
  isLoading: boolean;
  mode: "create" | "edit";
  initialData?: DatasetFormData;
}

const DatasetFormContent: React.FC<DatasetFormContentProps> = ({
  onClose,
  onSubmit,
  isLoading,
  mode,
  initialData,
}) => {
  const form = useForm({
    defaultValues: {
      name: initialData?.name || "",
      description: initialData?.description || "",
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

  const title = mode === "create" ? "Create Dataset" : "Edit Dataset";
  const submitText = mode === "create" ? "Create" : "Save";
  const loadingText = mode === "create" ? "Creating..." : "Saving...";

  return (
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          form.handleSubmit();
        }}
      >
        <DialogTitle id="dataset-form-dialog-title">{title}</DialogTitle>
        <DialogContent>
          <form.Field
            name="name"
            validators={{
              onChange: ({ value }) =>
                !value || value.trim().length === 0
                  ? "Dataset name is required"
                  : value.length > 100
                  ? "Dataset name must be less than 100 characters"
                  : undefined,
            }}
          >
            {(field) => (
              <TextField
                autoFocus
                margin="dense"
                label="Dataset Name"
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
                {isLoading ? loadingText : submitText}
              </Button>
            )}
          </form.Subscribe>
        </DialogActions>
      </form>
    </>
  );
};

export const DatasetFormModal: React.FC<DatasetFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  mode,
  initialData,
  datasetId,
}) => {
  const formKey =
    mode === "create" ? "create-new" : `edit-${datasetId || "unknown"}`;

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
      aria-labelledby="dataset-form-dialog-title"
    >
      <DatasetFormContent
        key={formKey}
        onClose={onClose}
        onSubmit={onSubmit}
        isLoading={isLoading}
        mode={mode}
        initialData={initialData}
      />
    </Dialog>
  );
};
