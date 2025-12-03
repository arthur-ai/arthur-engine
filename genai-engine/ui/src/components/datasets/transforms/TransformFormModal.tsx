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
import { useApi } from "@/hooks/useApi";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import type { DatasetResponse } from "@/lib/api-client/api-client";


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

  // State for copying from existing transform
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [selectedTransformId, setSelectedTransformId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState(false);

  const api = useApi();
  const { latestVersion } = useDatasetLatestVersion(datasetId);
  const datasetColumns = latestVersion?.column_names || [];

  // Fetch transforms for the selected dataset
  const { data: availableTransforms, isLoading: isLoadingTransforms } = useTransforms(selectedDatasetId || undefined);

  // Fetch datasets when modal opens (only for create mode, not edit)
  useEffect(() => {
    if (open && !initialTransform && api) {
      const fetchDatasets = async () => {
        try {
          setLoadingDatasets(true);
          const response = await api.api.getDatasetsApiV2DatasetsSearchGet({
            page_size: 100,
          });
          setDatasets(response.data.datasets || []);
        } catch (error) {
          console.error("Failed to load datasets:", error);
        } finally {
          setLoadingDatasets(false);
        }
      };
      fetchDatasets();
    }
  }, [open, initialTransform, api]);

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
      setSelectedDatasetId(null);
      setSelectedTransformId(null);
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

  const handleTransformSelect = (transformId: string | null) => {
    setSelectedTransformId(transformId);
    if (!transformId || !availableTransforms) return;

    const selectedTransform = availableTransforms.find((t) => t.id === transformId);
    if (selectedTransform) {
      // Populate form fields with the selected transform's data
      setName(selectedTransform.name);
      setDescription(selectedTransform.description || "");
      setColumns(
        selectedTransform.definition.columns.map((col) => ({
          column_name: col.column_name,
          span_name: col.span_name,
          attribute_path: col.attribute_path,
          fallback: col.fallback !== undefined && col.fallback !== null ? JSON.stringify(col.fallback) : "",
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

          {!initialTransform && (
            <>
              <Box>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
                  <ContentCopyIcon fontSize="small" color="action" />
                  <Typography variant="subtitle2" fontWeight="medium">
                    Copy from Existing Transform (Optional)
                  </Typography>
                </Box>
                <Stack spacing={2}>
                  <Autocomplete
                    options={datasets}
                    getOptionLabel={(option) => option.name || option.id}
                    value={datasets.find((d) => d.id === selectedDatasetId) || null}
                    onChange={(_, newValue) => {
                      setSelectedDatasetId(newValue?.id || null);
                      setSelectedTransformId(null); // Reset transform selection when dataset changes
                    }}
                    loading={loadingDatasets}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Select Dataset"
                        placeholder="Choose a dataset to copy a transform from"
                        size="small"
                        InputProps={{
                          ...params.InputProps,
                          endAdornment: (
                            <>
                              {loadingDatasets ? <CircularProgress color="inherit" size={20} /> : null}
                              {params.InputProps.endAdornment}
                            </>
                          ),
                        }}
                      />
                    )}
                  />

                  {selectedDatasetId && (
                    <Autocomplete
                      options={availableTransforms || []}
                      getOptionLabel={(option) => option.name}
                      value={availableTransforms?.find((t) => t.id === selectedTransformId) || null}
                      onChange={(_, newValue) => handleTransformSelect(newValue?.id || null)}
                      loading={isLoadingTransforms}
                      disabled={!selectedDatasetId || isLoadingTransforms}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Select Transform to Copy"
                          placeholder="Choose a transform"
                          size="small"
                          InputProps={{
                            ...params.InputProps,
                            endAdornment: (
                              <>
                                {isLoadingTransforms ? <CircularProgress color="inherit" size={20} /> : null}
                                {params.InputProps.endAdornment}
                              </>
                            ),
                          }}
                        />
                      )}
                    />
                  )}
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                  Select a dataset and transform to pre-fill the form below. You can modify the values as needed.
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
