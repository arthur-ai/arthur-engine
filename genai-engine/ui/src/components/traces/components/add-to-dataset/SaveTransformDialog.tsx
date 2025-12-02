import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Typography, Alert, Stack } from "@mui/material";
import { useState } from "react";

import { Column, TransformDefinition } from "./form/shared";
import { buildTransformFromColumns, validateTransform } from "./utils/transformBuilder";

interface SaveTransformDialogProps {
  open: boolean;
  onClose: () => void;
  columns: Column[];
  onSave: (name: string, description: string, definition: TransformDefinition) => Promise<void>;
}

// Dialog for saving manually extracted columns as a reusable transform
export function SaveTransformDialog({ open, onClose, columns, onSave }: SaveTransformDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const transformDef = buildTransformFromColumns(columns);

  const handleSave = async () => {
    const validationErrors: string[] = [];

    if (!name.trim()) {
      validationErrors.push("Transform name is required");
    }

    const defErrors = validateTransform(transformDef);
    validationErrors.push(...defErrors);

    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSaving(true);
    setErrors([]);

    try {
      await onSave(name.trim(), description.trim(), transformDef);
      setName("");
      setDescription("");
    } catch (err) {
      setErrors([err instanceof Error ? err.message : "Failed to save transform"]);
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    if (!isSaving) {
      setName("");
      setDescription("");
      setErrors([]);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Save as Transform</DialogTitle>
      <DialogContent>
        <Stack spacing={3} sx={{ mt: 1 }}>
          {errors.length > 0 && (
            <Alert severity="error">
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {errors.map((error, idx) => (
                  <li key={idx}>{error}</li>
                ))}
              </ul>
            </Alert>
          )}

          <TextField
            label="Transform Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Extract SQL Queries"
            required
            fullWidth
            autoFocus
          />

          <TextField
            label="Description (Optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this transform extracts"
            multiline
            rows={2}
            fullWidth
          />

          <div>
            <Typography variant="body2" fontWeight="medium" gutterBottom>
              Transform Definition (Preview)
            </Typography>
            <Typography variant="caption" color="text.secondary" gutterBottom display="block">
              This JSON will be saved and can be reused on future traces
            </Typography>
            <pre
              style={{
                backgroundColor: "#f5f5f5",
                padding: 16,
                borderRadius: 4,
                overflow: "auto",
                maxHeight: 300,
                fontSize: 12,
                border: "1px solid #e0e0e0",
              }}
            >
              {JSON.stringify(transformDef, null, 2)}
            </pre>
          </div>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isSaving}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save Transform"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
