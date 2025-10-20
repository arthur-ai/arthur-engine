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
import React, { useState, useCallback, useEffect } from "react";

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
  const [columns, setColumns] = useState<string[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");
  const [newColumnName, setNewColumnName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setColumns([...currentColumns]);
      setEditingIndex(null);
      setEditValue("");
      setNewColumnName("");
      setError(null);
    }
  }, [open, currentColumns]);

  const validateColumnName = useCallback(
    (name: string, excludeIndex?: number): string | null => {
      if (!name.trim()) {
        return "Column name is required";
      }
      if (name.length > 100) {
        return "Column name must be less than 100 characters";
      }
      const isDuplicate = columns.some(
        (col, idx) => col === name.trim() && idx !== excludeIndex
      );
      if (isDuplicate) {
        return "Column name already exists";
      }
      return null;
    },
    [columns]
  );

  const handleAddColumn = useCallback(() => {
    const validationError = validateColumnName(newColumnName);
    if (validationError) {
      setError(validationError);
      return;
    }

    setColumns((prev) => [...prev, newColumnName.trim()]);
    setNewColumnName("");
    setError(null);
  }, [newColumnName, validateColumnName]);

  const handleStartEdit = useCallback(
    (index: number) => {
      setEditingIndex(index);
      setEditValue(columns[index]);
      setError(null);
    },
    [columns]
  );

  const handleSaveEdit = useCallback(() => {
    if (editingIndex === null) return;

    const validationError = validateColumnName(editValue, editingIndex);
    if (validationError) {
      setError(validationError);
      return;
    }

    setColumns((prev) =>
      prev.map((col, idx) => (idx === editingIndex ? editValue.trim() : col))
    );
    setEditingIndex(null);
    setEditValue("");
    setError(null);
  }, [editingIndex, editValue, validateColumnName]);

  const handleCancelEdit = useCallback(() => {
    setEditingIndex(null);
    setEditValue("");
    setError(null);
  }, []);

  const handleDeleteColumn = useCallback((index: number) => {
    setColumns((prev) => prev.filter((_, idx) => idx !== index));
    setError(null);
  }, []);

  const handleSave = useCallback(() => {
    if (editingIndex !== null) {
      setError("Please save or cancel the current edit");
      return;
    }
    onSave(columns);
    onClose();
  }, [columns, editingIndex, onSave, onClose]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, action: "add" | "edit") => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (action === "add") {
          handleAddColumn();
        } else {
          handleSaveEdit();
        }
      } else if (event.key === "Escape") {
        event.preventDefault();
        if (action === "edit") {
          handleCancelEdit();
        }
      }
    },
    [handleAddColumn, handleSaveEdit, handleCancelEdit]
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      aria-labelledby="configure-columns-dialog-title"
    >
      <DialogTitle id="configure-columns-dialog-title">
        Configure Columns
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, py: 1 }}>
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
                    <>
                      <TextField
                        autoFocus
                        fullWidth
                        size="small"
                        value={editValue}
                        onChange={(e) => {
                          setEditValue(e.target.value);
                          setError(null);
                        }}
                        onKeyDown={(e) => handleKeyDown(e, "edit")}
                        error={!!error}
                        helperText={error}
                      />
                      <Button size="small" onClick={handleSaveEdit}>
                        Save
                      </Button>
                      <Button
                        size="small"
                        onClick={handleCancelEdit}
                        color="inherit"
                      >
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <>
                      <Typography sx={{ flexGrow: 1 }}>{column}</Typography>
                      <IconButton
                        size="small"
                        onClick={() => handleStartEdit(index)}
                        aria-label="edit column"
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteColumn(index)}
                        aria-label="delete column"
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </>
                  )}
                </ListItem>
              ))}
            </List>
          )}

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
              onKeyDown={(e) => handleKeyDown(e, "add")}
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
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          color="primary"
          disabled={editingIndex !== null}
        >
          Save Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
};
