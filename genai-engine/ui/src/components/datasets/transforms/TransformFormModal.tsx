import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Alert,
  Stack,
  Box,
  IconButton,
  Autocomplete,
} from "@mui/material";
import { useState, useEffect } from "react";

import { TransformFormModalProps } from "./types";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";


interface ColumnMapping {
  column_name: string;
  span_name: string;
  attribute_path: string;
  fallback: string;
}

export const TransformFormModal: React.FC<TransformFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading,
  datasetId,
  initialTransform,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [columns, setColumns] = useState<ColumnMapping[]>([
    { column_name: "", span_name: "", attribute_path: "", fallback: "" },
  ]);
  const [errors, setErrors] = useState<string[]>([]);
  const [importError, setImportError] = useState<string | null>(null);

  const { latestVersion } = useDatasetLatestVersion(datasetId);
  const datasetColumns = latestVersion?.column_names || [];

  useEffect(() => {
    if (initialTransform) {
      setName(initialTransform.name);
      setDescription(initialTransform.description || "");
      setColumns(
        initialTransform.definition.columns.map((col) => ({
          column_name: col.column_name,
          span_name: col.span_name,
          attribute_path: col.attribute_path,
          fallback: col.fallback !== undefined && col.fallback !== null ? JSON.stringify(col.fallback) : "",
        }))
      );
    } else {
      setName("");
      setDescription("");
      setColumns([{ column_name: "", span_name: "", attribute_path: "", fallback: "" }]);
    }
    setErrors([]);
  }, [initialTransform, open]);

  const handleAddColumn = () => {
    setColumns([...columns, { column_name: "", span_name: "", attribute_path: "", fallback: "" }]);
  };

  const handleRemoveColumn = (index: number) => {
    setColumns(columns.filter((_, i) => i !== index));
  };

  const handleColumnChange = (index: number, field: keyof ColumnMapping, value: string) => {
    const newColumns = [...columns];
    newColumns[index][field] = value;
    setColumns(newColumns);
  };

  const buildTransformDefinition = (): TransformDefinition => {
    return {
      columns: columns.map((col) => {
        let fallbackValue = undefined;
        if (col.fallback && col.fallback.trim()) {
          const parsed = JSON.parse(col.fallback);
          // Only set fallback if it's not null
          fallbackValue = parsed !== null ? parsed : undefined;
        }
        return {
          column_name: col.column_name,
          span_name: col.span_name,
          attribute_path: col.attribute_path,
          fallback: fallbackValue,
        };
      }),
    };
  };

  const handleSave = async () => {
    const validationErrors: string[] = [];

    if (!name.trim()) {
      validationErrors.push("Transform name is required");
    }

    if (columns.length === 0) {
      validationErrors.push("At least one column mapping is required");
    }

    columns.forEach((col, idx) => {
      if (!col.column_name.trim()) {
        validationErrors.push(`Column ${idx + 1}: Column name is required`);
      }
      if (!col.span_name.trim()) {
        validationErrors.push(`Column ${idx + 1}: Span name is required`);
      }
      if (!col.attribute_path.trim()) {
        validationErrors.push(`Column ${idx + 1}: Attribute path is required`);
      }
      if (col.fallback) {
        try {
          JSON.parse(col.fallback);
        } catch {
          validationErrors.push(`Column ${idx + 1}: Fallback must be valid JSON`);
        }
      }
    });

    try {
      const transformDef = buildTransformDefinition();
      const defErrors = validateTransform(transformDef);
      validationErrors.push(...defErrors);
    } catch {
      validationErrors.push("Invalid transform definition");
    }

    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors([]);

    try {
      const transformDef = buildTransformDefinition();
      await onSubmit(name.trim(), description.trim(), transformDef);
    } catch (err) {
      setErrors([err instanceof Error ? err.message : "Failed to save transform"]);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      onClose();
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportError(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const importedData = JSON.parse(content);

        // Validate the imported data structure
        if (!importedData.name || typeof importedData.name !== "string") {
          setImportError("Invalid JSON: 'name' field is required and must be a string");
          return;
        }

        if (!importedData.definition || !importedData.definition.columns || !Array.isArray(importedData.definition.columns)) {
          setImportError("Invalid JSON: 'definition.columns' must be an array");
          return;
        }

        // Validate each column
        for (const col of importedData.definition.columns) {
          if (!col.column_name || !col.span_name || !col.attribute_path) {
            setImportError("Invalid JSON: Each column must have column_name, span_name, and attribute_path");
            return;
          }
        }

        // Populate the form with imported data
        setName(importedData.name);
        setDescription(importedData.description || "");
        setColumns(
          importedData.definition.columns.map(
            (col: { column_name: string; span_name: string; attribute_path: string; fallback?: unknown }) => ({
              column_name: col.column_name,
              span_name: col.span_name,
              attribute_path: col.attribute_path,
              fallback: col.fallback !== undefined && col.fallback !== null ? JSON.stringify(col.fallback) : "",
            })
          )
        );
        setErrors([]);
      } catch (err) {
        setImportError(err instanceof Error ? err.message : "Failed to parse JSON file");
      }
    };

    reader.onerror = () => {
      setImportError("Failed to read file");
    };

    reader.readAsText(file);

    // Reset the input so the same file can be uploaded again
    event.target.value = "";
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>{initialTransform ? "Edit Transform" : "Create Transform"}</DialogTitle>
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

          {importError && (
            <Alert severity="error" onClose={() => setImportError(null)}>
              {importError}
            </Alert>
          )}

          {!initialTransform && (
            <Box>
              <input
                accept=".json"
                style={{ display: "none" }}
                id="transform-upload-file"
                type="file"
                onChange={handleFileUpload}
              />
              <label htmlFor="transform-upload-file">
                <Button component="span" startIcon={<UploadFileIcon />} variant="outlined" fullWidth>
                  Import from JSON File
                </Button>
              </label>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Upload a previously exported transform JSON file to populate this form
              </Typography>
            </Box>
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

          <Box>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="subtitle2" fontWeight="medium">
                Column Mappings
              </Typography>
              <Button startIcon={<AddIcon />} onClick={handleAddColumn} size="small">
                Add Column
              </Button>
            </Box>

            <Stack spacing={2}>
              {columns.map((col, idx) => (
                <Box
                  key={idx}
                  sx={{
                    p: 2,
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                    backgroundColor: "grey.50",
                  }}
                >
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                    <Typography variant="body2" fontWeight="medium">
                      Column {idx + 1}
                    </Typography>
                    <IconButton size="small" onClick={() => handleRemoveColumn(idx)} disabled={columns.length === 1}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>

                  <Stack spacing={2}>
                    <Autocomplete
                      freeSolo
                      options={datasetColumns}
                      value={col.column_name}
                      onChange={(_, newValue) => handleColumnChange(idx, "column_name", newValue || "")}
                      onInputChange={(_, newInputValue) => handleColumnChange(idx, "column_name", newInputValue)}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Dataset Column Name"
                          placeholder="e.g., sql_query"
                          size="small"
                          required
                        />
                      )}
                    />
                    <TextField
                      label="Span Name"
                      value={col.span_name}
                      onChange={(e) => handleColumnChange(idx, "span_name", e.target.value)}
                      placeholder="e.g., DatabaseQuery"
                      size="small"
                      required
                      fullWidth
                    />
                    <TextField
                      label="Attribute Path"
                      value={col.attribute_path}
                      onChange={(e) => handleColumnChange(idx, "attribute_path", e.target.value)}
                      placeholder="e.g., attributes.input.value"
                      size="small"
                      required
                      fullWidth
                    />
                    <TextField
                      label="Fallback Value (JSON, Optional)"
                      value={col.fallback}
                      onChange={(e) => handleColumnChange(idx, "fallback", e.target.value)}
                      placeholder='e.g., null or "default"'
                      size="small"
                      fullWidth
                    />
                  </Stack>
                </Box>
              ))}
            </Stack>
          </Box>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={isLoading}>
          {isLoading ? "Saving..." : initialTransform ? "Update Transform" : "Create Transform"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TransformFormModal;
