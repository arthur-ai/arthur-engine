import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import {
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  TextField,
  Typography,
} from "@mui/material";
import { useForm } from "@tanstack/react-form";
import React, { useState } from "react";
import { z } from "zod";

import { DefaultValueSelector } from "./DefaultValueSelector";

import { columnNameSchema } from "@/schemas/datasetSchemas";
import type { ColumnDefaultConfig, ColumnDefaults } from "@/types/dataset";

interface ConfigureColumnsModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (columns: string[], columnDefaults: ColumnDefaults, applyToExisting: boolean) => void;
  currentColumns: string[];
  currentColumnDefaults?: ColumnDefaults;
  existingRowCount?: number;
}

export const ConfigureColumnsModal: React.FC<ConfigureColumnsModalProps> = ({
  open,
  onClose,
  onSave,
  currentColumns,
  currentColumnDefaults = {},
  existingRowCount = 0,
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [newColumnName, setNewColumnName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [columnDefaults, setColumnDefaults] = useState<ColumnDefaults>(currentColumnDefaults);
  const [applyToExisting, setApplyToExisting] = useState(false);

  const form = useForm({
    defaultValues: {
      columns: currentColumns,
    },
    onSubmit: async ({ value }) => {
      onSave(value.columns, columnDefaults, applyToExisting);
      onClose();
      setEditingIndex(null);
      setNewColumnName("");
      setError(null);
      setApplyToExisting(false);
    },
  });

  const handleDefaultChange = (columnName: string, config: ColumnDefaultConfig) => {
    setColumnDefaults((prev) => ({
      ...prev,
      [columnName]: config,
    }));
  };

  const hasDefaultsConfigured = Object.values(columnDefaults).some((config) => config.type !== "none");

  const validateColumnName = (name: string, excludeIndex?: number): string | null => {
    const columns = form.getFieldValue("columns");

    try {
      columnNameSchema.parse(name);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return err.issues[0]?.message || "Invalid column name";
      }
    }

    const isDuplicate = columns.some((col: string, idx: number) => col === name.trim() && idx !== excludeIndex);

    if (isDuplicate) {
      return "Column name already exists";
    }

    return null;
  };

  const handleAddColumn = () => {
    const validationError = validateColumnName(newColumnName);
    if (validationError) {
      setError(validationError);
      return;
    }

    const currentColumns = form.getFieldValue("columns");
    form.setFieldValue("columns", [...currentColumns, newColumnName.trim()]);
    setNewColumnName("");
    setError(null);
  };

  const handleSaveEdit = (index: number, newValue: string) => {
    const validationError = validateColumnName(newValue, index);
    if (validationError) {
      setError(validationError);
      return;
    }

    const columns = form.getFieldValue("columns");
    const oldColumnName = columns[index];
    const newColumnName = newValue.trim();

    const updated = columns.map((col: string, idx: number) => (idx === index ? newColumnName : col));
    form.setFieldValue("columns", updated);

    // Transfer defaults from old column name to new column name
    if (oldColumnName !== newColumnName && columnDefaults[oldColumnName]) {
      setColumnDefaults((prev) => {
        const updated = { ...prev };
        updated[newColumnName] = updated[oldColumnName];
        delete updated[oldColumnName];
        return updated;
      });
    }

    setEditingIndex(null);
    setError(null);
  };

  const handleDeleteColumn = (index: number) => {
    const columns = form.getFieldValue("columns");
    const deletedColumn = columns[index];
    form.setFieldValue(
      "columns",
      columns.filter((_: string, idx: number) => idx !== index)
    );
    // Clean up the default config for the deleted column
    if (deletedColumn && columnDefaults[deletedColumn]) {
      setColumnDefaults((prev) => {
        const updated = { ...prev };
        delete updated[deletedColumn];
        return updated;
      });
    }
    setError(null);
  };

  const handleClose = () => {
    setEditingIndex(null);
    setNewColumnName("");
    setError(null);
    setColumnDefaults(currentColumnDefaults);
    setApplyToExisting(false);
    onClose();
  };

  const columnsKey = currentColumns.join(",");

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      aria-labelledby="configure-columns-dialog-title"
      slotProps={{
        paper: {
          sx: {
            maxHeight: "90vh",
            display: "flex",
            flexDirection: "column",
          },
        },
      }}
    >
      <form
        key={columnsKey}
        onSubmit={(e) => {
          e.preventDefault();
          if (editingIndex !== null) {
            setError("Please save or cancel the current edit");
            return;
          }
          form.handleSubmit();
        }}
        style={{
          display: "flex",
          flexDirection: "column",
          flex: 1,
          minHeight: 0,
        }}
      >
        <DialogTitle id="configure-columns-dialog-title">Configure Columns</DialogTitle>
        <DialogContent
          sx={{
            overflow: "auto",
            flex: 1,
            minHeight: 0,
          }}
        >
          <form.Field name="columns">
            {(field) => {
              const columns = field.state.value;

              return (
                <Box
                  sx={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 2,
                    py: 1,
                  }}
                >
                  {columns.length === 0 ? (
                    <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: "center" }}>
                      No columns yet. Add your first column below.
                    </Typography>
                  ) : (
                    <List sx={{ width: "100%", bgcolor: "background.paper" }}>
                      {columns.map((column, index) => (
                        <ListItem
                          key={index}
                          sx={{
                            border: 1,
                            borderColor: "divider",
                            borderRadius: 1,
                            mb: 1,
                            display: "flex",
                            alignItems: "center",
                            gap: 1,
                          }}
                        >
                          {editingIndex === index ? (
                            <EditingColumnRow
                              column={column}
                              onSave={(value) => handleSaveEdit(index, value)}
                              onCancel={() => setEditingIndex(null)}
                              error={error}
                              onErrorClear={() => setError(null)}
                            />
                          ) : (
                            <DisplayColumnRow
                              column={column}
                              defaultConfig={columnDefaults[column] ?? { type: "none" }}
                              onDefaultChange={(config) => handleDefaultChange(column, config)}
                              onEdit={() => {
                                setEditingIndex(index);
                                setError(null);
                              }}
                              onDelete={() => handleDeleteColumn(index)}
                            />
                          )}
                        </ListItem>
                      ))}
                    </List>
                  )}
                </Box>
              );
            }}
          </form.Field>
        </DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            gap: 1.5,
            position: "sticky",
            bottom: 0,
            backgroundColor: "background.paper",
            borderTop: 1,
            borderColor: "divider",
            zIndex: 1,
            px: 3,
            pt: 2,
            pb: 2,
          }}
        >
          <Box sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}>
            <TextField
              fullWidth
              size="small"
              label="New Column Name"
              placeholder="e.g., user_id, message, score"
              value={newColumnName}
              onChange={(e) => {
                setNewColumnName(e.target.value);
                setError(null);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddColumn();
                }
              }}
              error={!!error && editingIndex === null}
              helperText={editingIndex === null ? error : ""}
            />
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={handleAddColumn}
              disabled={!newColumnName.trim()}
              sx={{ minWidth: "100px", height: "40px" }}
            >
              Add
            </Button>
          </Box>

          {existingRowCount > 0 && hasDefaultsConfigured && (
            <FormControlLabel
              control={<Checkbox checked={applyToExisting} onChange={(e) => setApplyToExisting(e.target.checked)} size="small" />}
              label={
                <Typography variant="body2" color="text.secondary">
                  Apply defaults to existing rows ({existingRowCount} row
                  {existingRowCount !== 1 ? "s" : ""})
                </Typography>
              }
              sx={{ ml: 0 }}
            />
          )}

          <DialogActions>
            <Button onClick={handleClose} color="inherit">
              Cancel
            </Button>
            <Button type="submit" variant="contained" color="primary" disabled={editingIndex !== null}>
              Save Changes
            </Button>
          </DialogActions>
        </Box>
      </form>
    </Dialog>
  );
};

interface EditingColumnRowProps {
  column: string;
  onSave: (value: string) => void;
  onCancel: () => void;
  error: string | null;
  onErrorClear: () => void;
}

const EditingColumnRow: React.FC<EditingColumnRowProps> = ({ column, onSave, onCancel, error, onErrorClear }) => {
  const [value, setValue] = useState(column);

  return (
    <>
      <TextField
        autoFocus
        fullWidth
        size="small"
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          onErrorClear();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            onSave(value);
          } else if (e.key === "Escape") {
            e.preventDefault();
            onCancel();
          }
        }}
        error={!!error}
        helperText={error}
      />
      <Button size="small" onClick={() => onSave(value)}>
        Save
      </Button>
      <Button size="small" onClick={onCancel} color="inherit">
        Cancel
      </Button>
    </>
  );
};

interface DisplayColumnRowProps {
  column: string;
  defaultConfig: ColumnDefaultConfig;
  onDefaultChange: (config: ColumnDefaultConfig) => void;
  onEdit: () => void;
  onDelete: () => void;
}

const DisplayColumnRow: React.FC<DisplayColumnRowProps> = ({ column, defaultConfig, onDefaultChange, onEdit, onDelete }) => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      width: "100%",
      gap: 1,
    }}
  >
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <Typography sx={{ flexGrow: 1 }}>{column}</Typography>
      <IconButton size="small" onClick={onEdit} aria-label="edit column">
        <EditIcon fontSize="small" />
      </IconButton>
      <IconButton size="small" onClick={onDelete} color="error" aria-label="delete column">
        <DeleteIcon fontSize="small" />
      </IconButton>
    </Box>
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, pl: 1 }}>
      <Typography variant="body2" color="text.secondary" sx={{ minWidth: 60 }}>
        Default:
      </Typography>
      <DefaultValueSelector value={defaultConfig} onChange={onDefaultChange} />
    </Box>
  </Box>
);
