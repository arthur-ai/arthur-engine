import AddIcon from "@mui/icons-material/Add";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
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
  Divider,
  CircularProgress,
} from "@mui/material";
import { useState, useEffect } from "react";

import { useTransforms } from "./hooks/useTransforms";
import { TransformFormModalProps } from "./types";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";


interface VariableMapping {
  variable_name: string;
  span_name: string;
  attribute_path: string;
  fallback: string;
}

export const TransformFormModal: React.FC<TransformFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading,
  taskId,
  initialTransform,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [variables, setVariables] = useState<VariableMapping[]>([
    { variable_name: "", span_name: "", attribute_path: "", fallback: "" },
  ]);
  const [errors, setErrors] = useState<string[]>([]);

  // State for copying from existing transform
  const [selectedTransformId, setSelectedTransformId] = useState<string | null>(null);

  // Fetch transforms for the current task (for copying)
  const { data: availableTransforms, isLoading: isLoadingTransforms } = useTransforms(taskId);

  useEffect(() => {
    if (initialTransform) {
      setName(initialTransform.name);
      setDescription(initialTransform.description || "");
      setVariables(
        initialTransform.definition.variables.map((variable) => ({
          variable_name: variable.variable_name,
          span_name: variable.span_name,
          attribute_path: variable.attribute_path,
          fallback: variable.fallback !== undefined && variable.fallback !== null ? JSON.stringify(variable.fallback) : "",
        }))
      );
    } else {
      setName("");
      setDescription("");
      setVariables([{ variable_name: "", span_name: "", attribute_path: "", fallback: "" }]);
      setSelectedTransformId(null);
    }
    setErrors([]);
  }, [initialTransform, open]);

  const handleAddVariable = () => {
    setVariables([...variables, { variable_name: "", span_name: "", attribute_path: "", fallback: "" }]);
  };

  const handleRemoveVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const handleVariableChange = (index: number, field: keyof VariableMapping, value: string) => {
    const newVariables = [...variables];
    newVariables[index][field] = value;
    setVariables(newVariables);
  };

  const buildTransformDefinition = (): TransformDefinition => {
    return {
      variables: variables.map((variable) => {
        let fallbackValue = undefined;
        if (variable.fallback && variable.fallback.trim()) {
          const parsed = JSON.parse(variable.fallback);
          // Only set fallback if it's not null
          fallbackValue = parsed !== null ? parsed : undefined;
        }
        return {
          variable_name: variable.variable_name,
          span_name: variable.span_name,
          attribute_path: variable.attribute_path,
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

    if (variables.length === 0) {
      validationErrors.push("At least one variable mapping is required");
    }

    variables.forEach((variable, idx) => {
      if (!variable.variable_name.trim()) {
        validationErrors.push(`Variable ${idx + 1}: Variable name is required`);
      }
      if (!variable.span_name.trim()) {
        validationErrors.push(`Variable ${idx + 1}: Span name is required`);
      }
      if (!variable.attribute_path.trim()) {
        validationErrors.push(`Variable ${idx + 1}: Attribute path is required`);
      }
      if (variable.fallback) {
        try {
          JSON.parse(variable.fallback);
        } catch {
          validationErrors.push(`Variable ${idx + 1}: Fallback must be valid JSON`);
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

  const handleTransformSelect = (transformId: string | null) => {
    setSelectedTransformId(transformId);
    if (!transformId || !availableTransforms) return;

    const selectedTransform = availableTransforms.find((t) => t.id === transformId);
    if (selectedTransform) {
      // Populate form fields with the selected transform's data
      setName(selectedTransform.name);
      setDescription(selectedTransform.description || "");
      setVariables(
        selectedTransform.definition.variables.map((variable) => ({
          variable_name: variable.variable_name,
          span_name: variable.span_name,
          attribute_path: variable.attribute_path,
          fallback: variable.fallback !== undefined && variable.fallback !== null ? JSON.stringify(variable.fallback) : "",
        }))
      );
      setErrors([]);
    }
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

          {!initialTransform && availableTransforms && availableTransforms.length > 0 && (
            <>
              <Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                  <ContentCopyIcon fontSize="small" color="action" />
                  <Typography variant="subtitle2" fontWeight="medium">
                    Copy from Existing Transform (Optional)
                  </Typography>
                </Box>
                <Autocomplete
                  options={availableTransforms || []}
                  getOptionLabel={(option) => option.name}
                  value={availableTransforms?.find((t) => t.id === selectedTransformId) || null}
                  onChange={(_, newValue) => handleTransformSelect(newValue?.id || null)}
                  loading={isLoadingTransforms}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Select Transform to Copy"
                      placeholder="Choose a transform"
                      size="small"
                      slotProps={{
                        input: {
                          ...params.InputProps,
                          endAdornment: (
                            <>
                              {isLoadingTransforms ? <CircularProgress color="inherit" size={20} /> : null}
                              {params.InputProps.endAdornment}
                            </>
                          ),
                        },
                      }}
                    />
                  )}
                />
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                  Select an existing transform to pre-fill the form below. You can modify the values as needed.
                </Typography>
              </Box>
              <Divider />
            </>
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
                Variable Mappings
              </Typography>
              <Button startIcon={<AddIcon />} onClick={handleAddVariable} size="small">
                Add Variable
              </Button>
            </Box>

            <Stack spacing={2}>
              {variables.map((variable, idx) => (
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
                      Variable {idx + 1}
                    </Typography>
                    <IconButton size="small" onClick={() => handleRemoveVariable(idx)} disabled={variables.length === 1}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>

                  <Stack spacing={2}>
                    <TextField
                      label="Variable Name"
                      value={variable.variable_name}
                      onChange={(e) => handleVariableChange(idx, "variable_name", e.target.value)}
                      placeholder="e.g., sql_query"
                      size="small"
                      required
                      fullWidth
                    />
                    <TextField
                      label="Span Name"
                      value={variable.span_name}
                      onChange={(e) => handleVariableChange(idx, "span_name", e.target.value)}
                      placeholder="e.g., DatabaseQuery"
                      size="small"
                      required
                      fullWidth
                    />
                    <TextField
                      label="Attribute Path"
                      value={variable.attribute_path}
                      onChange={(e) => handleVariableChange(idx, "attribute_path", e.target.value)}
                      placeholder="e.g., attributes.input.value"
                      size="small"
                      required
                      fullWidth
                    />
                    <TextField
                      label="Fallback Value (JSON, Optional)"
                      value={variable.fallback}
                      onChange={(e) => handleVariableChange(idx, "fallback", e.target.value)}
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
