import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  TextField,
  Typography,
} from "@mui/material";
import { useForm } from "@tanstack/react-form";
import React, { useState } from "react";
import { z } from "zod";

import { columnNameSchema } from "@/schemas/datasetSchemas";

interface ConfigureColumnsModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (columns: string[]) => void;
  currentColumns: string[];
}

export const ConfigureColumnsModal: React.FC<ConfigureColumnsModalProps> = ({
  open,
  onClose,
  onSave,
  currentColumns,
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [newColumnName, setNewColumnName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const form = useForm({
    defaultValues: {
      columns: currentColumns,
    },
    onSubmit: async ({ value }) => {
      onSave(value.columns);
      onClose();
      setEditingIndex(null);
      setNewColumnName("");
      setError(null);
    },
  });

  const validateColumnName = (
    name: string,
    excludeIndex?: number
  ): string | null => {
    const columns = form.getFieldValue("columns");

    try {
      columnNameSchema.parse(name);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return err.issues[0]?.message || "Invalid column name";
      }
    }

    const isDuplicate = columns.some(
      (col: string, idx: number) => col === name.trim() && idx !== excludeIndex
    );

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
    const updated = columns.map((col: string, idx: number) =>
      idx === index ? newValue.trim() : col
    );
    form.setFieldValue("columns", updated);
    setEditingIndex(null);
    setError(null);
  };

  const handleDeleteColumn = (index: number) => {
    const columns = form.getFieldValue("columns");
    form.setFieldValue(
      "columns",
      columns.filter((_: string, idx: number) => idx !== index)
    );
    setError(null);
  };

  const handleClose = () => {
    setEditingIndex(null);
    setNewColumnName("");
    setError(null);
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
        <DialogTitle id="configure-columns-dialog-title">
          Configure Columns
        </DialogTitle>
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
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ py: 2, textAlign: "center" }}
                    >
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

          <DialogActions>
            <Button onClick={handleClose} color="inherit">
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              color="primary"
              disabled={editingIndex !== null}
            >
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

const EditingColumnRow: React.FC<EditingColumnRowProps> = ({
  column,
  onSave,
  onCancel,
  error,
  onErrorClear,
}) => {
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
  onEdit: () => void;
  onDelete: () => void;
}

const DisplayColumnRow: React.FC<DisplayColumnRowProps> = ({
  column,
  onEdit,
  onDelete,
}) => (
  <>
    <Typography sx={{ flexGrow: 1 }}>{column}</Typography>
    <IconButton size="small" onClick={onEdit} aria-label="edit column">
      <EditIcon fontSize="small" />
    </IconButton>
    <IconButton
      size="small"
      onClick={onDelete}
      color="error"
      aria-label="delete column"
    >
      <DeleteIcon fontSize="small" />
    </IconButton>
  </>
);
