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

interface CreateDatasetModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (name: string, description: string) => Promise<void>;
  isLoading: boolean;
}

export const CreateDatasetModal: React.FC<CreateDatasetModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) {
      setError("Dataset name is required");
      return;
    }

    try {
      await onSubmit(name.trim(), description.trim());
      setName("");
      setDescription("");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create dataset");
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setName("");
      setDescription("");
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create New Dataset</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label="Dataset Name"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setError(null);
            }}
            placeholder="e.g., User Feedback Samples"
            required
            fullWidth
            autoFocus
            error={!!error}
            helperText={error}
            disabled={isLoading}
          />

          <TextField
            label="Description (Optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the purpose of this dataset"
            multiline
            rows={3}
            fullWidth
            disabled={isLoading}
          />
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={isLoading || !name.trim()}>
          {isLoading ? "Creating..." : "Create Dataset"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CreateDatasetModal;
