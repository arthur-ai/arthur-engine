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
  MenuItem,
} from "@mui/material";
import { useState, useEffect } from "react";

import { useTransforms } from "./hooks/useTransforms";
import { useTransformVersions } from "./hooks/useTransformVersions";
import { TransformFormModalProps } from "./types";
import { emptyVariableRow, rowToVariable, SPAN_SELECTORS, validateVariableRow, variableToRow, type VariableRow } from "./variableRows";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";

export const TransformFormModal: React.FC<TransformFormModalProps> = ({
  open,
  onClose,
  onSubmit,
  isLoading,
  taskId,
  initialTransform,
  initialVariableNames,
}) => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [variables, setVariables] = useState<VariableRow[]>([emptyVariableRow()]);
  const [errors, setErrors] = useState<string[]>([]);

  // State for copying from existing transform
  const [selectedTransformId, setSelectedTransformId] = useState<string | null>(null);

  // Fetch transforms for the current task (for copying)
  const { data: availableTransforms, isLoading: isLoadingTransforms } = useTransforms(taskId);

  // Fetch latest version for the transform being edited
  const { data: initialTransformVersions = [] } = useTransformVersions(initialTransform?.id);
  const initialTransformDefinition = initialTransformVersions[0]?.definition;

  // Fetch latest version for the transform being copied from
  const { data: copyTransformVersions = [] } = useTransformVersions(selectedTransformId ?? undefined);
  const copyTransformDefinition = copyTransformVersions[0]?.definition;

  useEffect(() => {
    if (initialTransform) {
      setName(initialTransform.name);
      setDescription(initialTransform.description || "");
      if (initialTransformDefinition) {
        setVariables(initialTransformDefinition.variables.map(variableToRow));
      }
    } else if (initialVariableNames && initialVariableNames.length > 0) {
      setName("");
      setDescription("");
      setVariables(initialVariableNames.map((name) => emptyVariableRow(name)));
      setSelectedTransformId(null);
    } else {
      setName("");
      setDescription("");
      setVariables([emptyVariableRow()]);
      setSelectedTransformId(null);
    }
    setErrors([]);
  }, [initialTransform, initialTransformDefinition, initialVariableNames, open]);

  const handleAddVariable = () => {
    setVariables([...variables, emptyVariableRow()]);
  };

  const handleRemoveVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const handleVariableChange = <K extends keyof VariableRow>(index: number, field: K, value: VariableRow[K]) => {
    setVariables(variables.map((variable, i) => (i === index ? { ...variable, [field]: value } : variable)));
  };

  const buildTransformDefinition = (): TransformDefinition => ({ variables: variables.map(rowToVariable) });

  const handleSave = async () => {
    const validationErrors: string[] = [];

    if (!name.trim()) {
      validationErrors.push("Transform name is required");
    }

    if (variables.length === 0) {
      validationErrors.push("At least one variable mapping is required");
    }

    variables.forEach((variable, idx) => validationErrors.push(...validateVariableRow(variable, idx)));

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

  // Populate form when version data loads for the selected copy-from transform
  useEffect(() => {
    if (!selectedTransformId || !copyTransformDefinition || !availableTransforms) return;
    const selectedTransform = availableTransforms.find((t) => t.id === selectedTransformId);
    if (selectedTransform) {
      setName(selectedTransform.name);
      setDescription(selectedTransform.description || "");
      setVariables(copyTransformDefinition.variables.map(variableToRow));
      setErrors([]);
    }
  }, [selectedTransformId, copyTransformDefinition, availableTransforms]);

  const handleTransformSelect = (transformId: string | null) => {
    setSelectedTransformId(transformId);
    // Form fields are populated reactively via useEffect above once version data loads
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
                  <Typography
                    variant="subtitle2"
                    sx={{
                      fontWeight: "medium",
                    }}
                  >
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
                        ...params.slotProps,

                        input: {
                          ...params.slotProps.input,
                          endAdornment: (
                            <>
                              {isLoadingTransforms ? <CircularProgress color="inherit" size={20} /> : null}
                              {params.slotProps.input.endAdornment}
                            </>
                          ),
                        },
                      }}
                    />
                  )}
                />
                <Typography
                  variant="caption"
                  sx={{
                    color: "text.secondary",
                    display: "block",
                    mt: 1,
                  }}
                >
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
              <Typography
                variant="subtitle2"
                sx={{
                  fontWeight: "medium",
                }}
              >
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
                    backgroundColor: "action.hover",
                  }}
                >
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: "medium",
                      }}
                    >
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
                    <Stack direction="row" spacing={2}>
                      <TextField
                        label="Span Name"
                        value={variable.span_name}
                        onChange={(e) => handleVariableChange(idx, "span_name", e.target.value)}
                        placeholder="e.g., DatabaseQuery"
                        size="small"
                        fullWidth
                      />
                      <TextField
                        label="Span Kind (Optional)"
                        value={variable.span_kind}
                        onChange={(e) => handleVariableChange(idx, "span_kind", e.target.value)}
                        placeholder="e.g., TOOL"
                        helperText="Alone, matches every span of this kind"
                        size="small"
                        fullWidth
                      />
                    </Stack>
                    <TextField
                      select
                      label="When Several Spans Match"
                      value={variable.span_selector}
                      onChange={(e) => handleVariableChange(idx, "span_selector", e.target.value as VariableRow["span_selector"])}
                      helperText={SPAN_SELECTORS.find((s) => s.value === variable.span_selector)?.help}
                      size="small"
                      fullWidth
                    >
                      {SPAN_SELECTORS.map((selector) => (
                        <MenuItem key={selector.value} value={selector.value}>
                          {selector.label}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      label="Attribute Path"
                      value={variable.attribute_path}
                      onChange={(e) => handleVariableChange(idx, "attribute_path", e.target.value)}
                      placeholder="e.g., attributes.input.value or attributes.results.*.name"
                      helperText="Use * to extract from all items in an array"
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
