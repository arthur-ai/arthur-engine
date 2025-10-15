import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from "@mui/material";
import React, { useState, useCallback, useEffect, useMemo } from "react";
import { z } from "zod";

interface EditRowModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (rowData: Record<string, unknown>) => Promise<void>;
  rowData: Record<string, unknown>;
  rowId: string;
  isLoading?: boolean;
}

// Helper function to infer Zod schema from JSONB data
const inferSchemaFromJSONB = (
  data: Record<string, unknown>,
  isNewRow: boolean = false
): z.ZodObject<Record<string, z.ZodTypeAny>> => {
  const shape: Record<string, z.ZodTypeAny> = {};

  Object.entries(data).forEach(([key, value]) => {
    // For new rows (empty strings), require non-empty values
    if (isNewRow && value === "") {
      shape[key] = z
        .string()
        .min(1, { message: "This field is required" })
        .or(z.number())
        .or(z.boolean());
    } else if (value === null || value === undefined) {
      // Nullable/optional field
      shape[key] = z
        .union([z.string(), z.number(), z.boolean(), z.null()])
        .nullable()
        .optional();
    } else if (typeof value === "boolean") {
      shape[key] = z.boolean({
        message: 'Must be "true" or "false"',
      });
    } else if (typeof value === "number") {
      shape[key] = z.number({
        message: "Must be a valid number",
      });
    } else if (typeof value === "string") {
      // For existing strings, require non-empty
      shape[key] = z.string().min(1, { message: "This field cannot be empty" });
    } else if (Array.isArray(value)) {
      shape[key] = z.array(z.unknown());
    } else if (typeof value === "object") {
      // For JSON objects, accept any structure - use z.any() for flexibility
      shape[key] = z.any();
    } else {
      // Fallback for any other type
      shape[key] = z.any();
    }
  });

  return z.object(shape);
};

export const EditRowModal: React.FC<EditRowModalProps> = ({
  open,
  onClose,
  onSubmit,
  rowData,
  rowId,
  isLoading = false,
}) => {
  const [editedData, setEditedData] = useState<Record<string, unknown>>({});
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});
  const [error, setError] = useState<string | null>(null);

  // Determine if this is a new row (all values are empty strings)
  const isNewRow = useMemo(() => {
    return Object.values(rowData).every((val) => val === "");
  }, [rowData]);

  // Infer Zod schema from original row data structure
  const schema = useMemo(
    () => inferSchemaFromJSONB(rowData, isNewRow),
    [rowData, isNewRow]
  );

  // Initialize edited data when modal opens or rowData changes
  useEffect(() => {
    if (open) {
      setEditedData({ ...rowData });
      setValidationErrors({});
      setError(null);
    }
  }, [open, rowData]);

  const handleClose = useCallback(() => {
    if (!isLoading) {
      setEditedData({ ...rowData });
      setValidationErrors({});
      setError(null);
      onClose();
    }
  }, [isLoading, onClose, rowData]);

  const handleFieldChange = useCallback(
    (key: string, inputValue: string) => {
      const originalValue = rowData[key];
      let parsedValue: unknown = inputValue;

      // Parse based on original type for better UX
      if (typeof originalValue === "number") {
        const num = Number(inputValue);
        parsedValue = inputValue === "" ? null : num;
      } else if (typeof originalValue === "boolean") {
        const lower = inputValue.toLowerCase();
        if (lower === "true") parsedValue = true;
        else if (lower === "false") parsedValue = false;
        else parsedValue = inputValue; // Let Zod validate
      } else if (typeof originalValue === "object" && originalValue !== null) {
        // Try to parse JSON for objects/arrays
        try {
          parsedValue = inputValue.trim() ? JSON.parse(inputValue) : null;
        } catch {
          parsedValue = inputValue; // Let Zod validate
        }
      } else if (inputValue === "") {
        parsedValue = null;
      }

      setEditedData((prev) => ({
        ...prev,
        [key]: parsedValue,
      }));

      // Clear validation error for this field
      setValidationErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[key];
        return newErrors;
      });
    },
    [rowData]
  );

  const handleSubmit = useCallback(async () => {
    setError(null);
    setValidationErrors({});

    try {
      // Validate data against inferred schema
      const validatedData = schema.parse(editedData);

      // Submit validated data
      await onSubmit(validatedData);

      // Reset on success
      setEditedData({ ...rowData });
      setValidationErrors({});
      setError(null);
    } catch (err) {
      if (err instanceof z.ZodError) {
        // Handle Zod validation errors
        const fieldErrors: Record<string, string> = {};
        err.issues.forEach((issue) => {
          const field = issue.path[0] as string;
          fieldErrors[field] = issue.message;
        });
        setValidationErrors(fieldErrors);
        setError("Please fix the validation errors.");
      } else {
        console.error("Failed to update row:", err);
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to update row. Please try again.";
        setError(errorMessage);
      }
    }
  }, [editedData, schema, onSubmit, rowData]);

  const columns = Object.keys(rowData);

  const formatValueForDisplay = (value: unknown): string => {
    if (value === null || value === undefined) return "";
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    return String(value);
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="edit-row-dialog-title"
    >
      <DialogTitle id="edit-row-dialog-title">
        Edit Row: <code style={{ fontSize: "0.85em" }}>{rowId}</code>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, mt: 1 }}>
          {columns.map((column) => {
            const value = editedData[column];
            const originalValue = rowData[column];
            const isMultiline =
              typeof originalValue === "object" ||
              (typeof value === "string" && value.length > 50);

            return (
              <Box key={column}>
                <TextField
                  label={column}
                  value={formatValueForDisplay(value)}
                  onChange={(e) => handleFieldChange(column, e.target.value)}
                  disabled={isLoading}
                  fullWidth
                  size="small"
                  multiline={isMultiline}
                  rows={isMultiline ? 3 : 1}
                  error={!!validationErrors[column]}
                  helperText={validationErrors[column] || " "}
                />
              </Box>
            );
          })}
        </Box>

        {/* Global error message */}
        {error && (
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            {error}
          </Typography>
        )}
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
          {isLoading ? "Saving..." : "Save Changes"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
