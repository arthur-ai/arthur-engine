import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  CircularProgress,
} from "@mui/material";
import React, { useState, useCallback, useEffect } from "react";

import { DatasetFormData } from "@/types/dataset";

interface DatasetFormModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: DatasetFormData) => Promise<void>;
  isLoading?: boolean;
  mode: "create" | "edit";
  initialData?: DatasetFormData;
}

export const DatasetFormModal: React.FC<DatasetFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading = false,
  mode,
  initialData,
}) => {
  const [formData, setFormData] = useState<DatasetFormData>({
    name: "",
    description: "",
  });
  const [errors, setErrors] = useState<{ name?: string; description?: string }>(
    {}
  );

  useEffect(() => {
    if (open && initialData) {
      setFormData({
        name: initialData.name || "",
        description: initialData.description || "",
      });
    } else if (open && !initialData) {
      setFormData({ name: "", description: "" });
    }
  }, [open, initialData]);

  const validateForm = useCallback((): boolean => {
    const newErrors: { name?: string; description?: string } = {};

    if (!formData.name.trim()) {
      newErrors.name = "Dataset name is required";
    } else if (formData.name.length > 100) {
      newErrors.name = "Dataset name must be less than 100 characters";
    }

    if (formData.description && formData.description.length > 500) {
      newErrors.description = "Description must be less than 500 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  const handleSubmit = useCallback(async () => {
    if (!validateForm()) {
      return;
    }

    try {
      await onSubmit(formData);
      setFormData({ name: "", description: "" });
      setErrors({});
    } catch (error) {
      console.error(`Failed to ${mode} dataset:`, error);
    }
  }, [formData, onSubmit, validateForm, mode]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      setFormData({ name: "", description: "" });
      setErrors({});
      onClose();
    }
  }, [isLoading, onClose]);

  const handleKeyPress = useCallback(
    (event: React.KeyboardEvent) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const title = mode === "create" ? "Create Dataset" : "Edit Dataset";
  const submitText = mode === "create" ? "Create" : "Save";
  const loadingText = mode === "create" ? "Creating..." : "Saving...";

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      aria-labelledby="dataset-form-dialog-title"
    >
      <DialogTitle id="dataset-form-dialog-title">{title}</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          margin="dense"
          id="dataset-name"
          label="Dataset Name"
          type="text"
          fullWidth
          variant="outlined"
          required
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          error={!!errors.name}
          helperText={errors.name}
          disabled={isLoading}
          onKeyPress={handleKeyPress}
          sx={{ mt: 2 }}
        />
        <TextField
          margin="dense"
          id="dataset-description"
          label="Description (Optional)"
          type="text"
          fullWidth
          variant="outlined"
          multiline
          rows={3}
          value={formData.description}
          onChange={(e) =>
            setFormData({ ...formData, description: e.target.value })
          }
          error={!!errors.description}
          helperText={errors.description}
          disabled={isLoading}
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isLoading} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isLoading || !formData.name.trim()}
          variant="contained"
          color="primary"
          startIcon={isLoading ? <CircularProgress size={16} /> : null}
        >
          {isLoading ? loadingText : submitText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
