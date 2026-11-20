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
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import { useState, useEffect } from "react";

import { useTransforms } from "./hooks/useTransforms";
import { useTransformVersions } from "./hooks/useTransformVersions";
import { TransformFormModalProps } from "./types";
import { DEFAULT_TRACE_MAX_CHARS, MIN_TRACE_MAX_CHARS, VARIABLE_SOURCES, validateMaxChars } from "./variableSource";

import { TransformDefinition } from "@/components/traces/components/add-to-dataset/form/shared";
import { validateTransform } from "@/components/traces/components/add-to-dataset/utils/transformBuilder";
import type { TraceTransformVariableDefinition, TransformVariableSource } from "@/lib/api-client/api-client";

interface VariableMapping {
  variable_name: string;
  source: TransformVariableSource;
  span_name: string;
  attribute_path: string;
  fallback: string;
  // Typed text; empty means the default budget
  max_chars: string;
}

const emptyVariable = (variable_name = ""): VariableMapping => ({
  variable_name,
  source: "span",
  span_name: "",
  attribute_path: "",
  fallback: "",
  max_chars: "",
});

const toVariableMapping = (variable: TraceTransformVariableDefinition): VariableMapping => ({
  variable_name: variable.variable_name,
  source: variable.source ?? "span",
  span_name: variable.span_name,
  attribute_path: variable.attribute_path,
  fallback: variable.fallback !== undefined && variable.fallback !== null ? JSON.stringify(variable.fallback) : "",
  max_chars: variable.max_chars != null ? String(variable.max_chars) : "",
});

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
  const [variables, setVariables] = useState<VariableMapping[]>([emptyVariable()]);
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
        setVariables(initialTransformDefinition.variables.map(toVariableMapping));
      }
    } else if (initialVariableNames && initialVariableNames.length > 0) {
      setName("");
      setDescription("");
      setVariables(initialVariableNames.map((name) => emptyVariable(name)));
      setSelectedTransformId(null);
    } else {
      setName("");
      setDescription("");
      setVariables([emptyVariable()]);
      setSelectedTransformId(null);
    }
    setErrors([]);
  }, [initialTransform, initialTransformDefinition, initialVariableNames, open]);

  const handleAddVariable = () => {
    setVariables([...variables, emptyVariable()]);
  };

  const handleRemoveVariable = (index: number) => {
    setVariables(variables.filter((_, i) => i !== index));
  };

  const handleVariableChange = (index: number, field: Exclude<keyof VariableMapping, "source">, value: string) => {
    const newVariables = [...variables];
    newVariables[index][field] = value;
    setVariables(newVariables);
  };

  const handleSourceChange = (index: number, source: TransformVariableSource) => {
    setVariables(variables.map((variable, i) => (i === index ? { ...variable, source } : variable)));
  };

  const buildTransformDefinition = (): TransformDefinition => {
    return {
      variables: variables.map((variable) => {
        if (variable.source === "trace") {
          // The whole trace names no span or attribute; the API keeps both as strings
          return {
            variable_name: variable.variable_name,
            source: "trace",
            span_name: "",
            attribute_path: "",
            max_chars: variable.max_chars.trim() ? Number(variable.max_chars) : undefined,
          };
        }
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
          max_chars: variable.max_chars.trim() ? Number(variable.max_chars) : undefined,
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
      const maxCharsError = validateMaxChars(variable.max_chars);
      if (maxCharsError) {
        validationErrors.push(`Variable ${idx + 1}: ${maxCharsError}`);
      }
      if (variable.source === "trace") {
        return;
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

  // Populate form when version data loads for the selected copy-from transform
  useEffect(() => {
    if (!selectedTransformId || !copyTransformDefinition || !availableTransforms) return;
    const selectedTransform = availableTransforms.find((t) => t.id === selectedTransformId);
    if (selectedTransform) {
      setName(selectedTransform.name);
      setDescription(selectedTransform.description || "");
      setVariables(copyTransformDefinition.variables.map(toVariableMapping));
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
                    <Box>
                      <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 0.5 }}>
                        Value comes from
                      </Typography>
                      <ToggleButtonGroup
                        exclusive
                        size="small"
                        value={variable.source}
                        onChange={(_, source: TransformVariableSource | null) => source && handleSourceChange(idx, source)}
                      >
                        {VARIABLE_SOURCES.map((option) => (
                          <ToggleButton key={option.value} value={option.value}>
                            {option.label}
                          </ToggleButton>
                        ))}
                      </ToggleButtonGroup>
                      <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 0.5 }}>
                        {VARIABLE_SOURCES.find((option) => option.value === variable.source)?.description}
                      </Typography>
                    </Box>
                    {variable.source === "span" && (
                      <>
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
                      </>
                    )}
                    <TextField
                      label="Size Budget (characters, Optional)"
                      value={variable.max_chars}
                      onChange={(e) => handleVariableChange(idx, "max_chars", e.target.value)}
                      placeholder={DEFAULT_TRACE_MAX_CHARS.toLocaleString()}
                      helperText={
                        variable.source === "trace"
                          ? `Default ${DEFAULT_TRACE_MAX_CHARS.toLocaleString()}, at least ${MIN_TRACE_MAX_CHARS.toLocaleString()}. Over it, long fields are shortened and middle spans left out, and the text says what was cut.`
                          : `Applies when several spans match: their joined value stays within it (default ${DEFAULT_TRACE_MAX_CHARS.toLocaleString()}, at least ${MIN_TRACE_MAX_CHARS.toLocaleString()}). A single match is never cut.`
                      }
                      size="small"
                      type="number"
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
