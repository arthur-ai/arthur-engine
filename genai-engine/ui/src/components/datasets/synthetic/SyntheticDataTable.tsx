import { Add, Delete } from "@mui/icons-material";
import {
  Box,
  Button,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import React, { useCallback, useState } from "react";

import type { SyntheticRow } from "./types";

interface SyntheticDataTableProps {
  rows: SyntheticRow[];
  columns: string[];
  onUpdateRow: (id: string, data: Record<string, string>) => void;
  onAddRow: (data: Record<string, string>) => void;
  onDeleteRows: (ids: string[]) => void;
}

export const SyntheticDataTable: React.FC<SyntheticDataTableProps> = ({
  rows,
  columns,
  onUpdateRow,
  onAddRow,
  onDeleteRows,
}) => {
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const [editingCell, setEditingCell] = useState<{
    rowId: string;
    column: string;
  } | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (checked) {
        setSelectedRows(new Set(rows.map((r) => r.id)));
      } else {
        setSelectedRows(new Set());
      }
    },
    [rows]
  );

  const handleSelectRow = useCallback((rowId: string, checked: boolean) => {
    setSelectedRows((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(rowId);
      } else {
        next.delete(rowId);
      }
      return next;
    });
  }, []);

  const handleDeleteSelected = useCallback(() => {
    onDeleteRows(Array.from(selectedRows));
    setSelectedRows(new Set());
  }, [selectedRows, onDeleteRows]);

  const handleCellClick = useCallback(
    (rowId: string, column: string, currentValue: string) => {
      setEditingCell({ rowId, column });
      setEditValue(currentValue);
    },
    []
  );

  const handleCellBlur = useCallback(() => {
    if (editingCell) {
      const row = rows.find((r) => r.id === editingCell.rowId);
      if (row) {
        const newData = { ...row.data, [editingCell.column]: editValue };
        onUpdateRow(editingCell.rowId, newData);
      }
    }
    setEditingCell(null);
    setEditValue("");
  }, [editingCell, editValue, rows, onUpdateRow]);

  const handleCellKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleCellBlur();
      } else if (e.key === "Escape") {
        setEditingCell(null);
        setEditValue("");
      }
    },
    [handleCellBlur]
  );

  const handleAddRow = useCallback(() => {
    const emptyRow: Record<string, string> = {};
    columns.forEach((col) => {
      emptyRow[col] = "";
    });
    onAddRow(emptyRow);
  }, [columns, onAddRow]);

  const allSelected = rows.length > 0 && selectedRows.size === rows.length;
  const someSelected = selectedRows.size > 0 && selectedRows.size < rows.length;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Toolbar */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          p: 2,
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Typography variant="subtitle2">
          Generated Data ({rows.length} row{rows.length !== 1 ? "s" : ""})
        </Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          {selectedRows.size > 0 && (
            <Button
              size="small"
              color="error"
              startIcon={<Delete />}
              onClick={handleDeleteSelected}
            >
              Delete ({selectedRows.size})
            </Button>
          )}
          <Button size="small" startIcon={<Add />} onClick={handleAddRow}>
            Add Row
          </Button>
        </Box>
      </Box>

      {/* Table */}
      <TableContainer sx={{ flex: 1, overflow: "auto" }}>
        {rows.length === 0 ? (
          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "text.secondary",
            }}
          >
            <Typography variant="body2">
              No data generated yet. Use the chat to generate or refine data.
            </Typography>
          </Box>
        ) : (
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ bgcolor: "grey.100" }}>
                  <Checkbox
                    checked={allSelected}
                    indeterminate={someSelected}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                  />
                </TableCell>
                {columns.map((column) => (
                  <TableCell
                    key={column}
                    sx={{
                      fontWeight: "bold",
                      bgcolor: "grey.100",
                      minWidth: 150,
                    }}
                  >
                    {column}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow
                  key={row.id}
                  hover
                  selected={selectedRows.has(row.id)}
                  sx={{
                    bgcolor:
                      row.status === "added"
                        ? "success.50"
                        : row.status === "modified"
                          ? "warning.50"
                          : "inherit",
                  }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedRows.has(row.id)}
                      onChange={(e) => handleSelectRow(row.id, e.target.checked)}
                    />
                  </TableCell>
                  {columns.map((column) => {
                    const isEditing =
                      editingCell?.rowId === row.id &&
                      editingCell?.column === column;
                    const value = row.data[column] || "";

                    return (
                      <TableCell key={column}>
                        {isEditing ? (
                          <TextField
                            autoFocus
                            size="small"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={handleCellBlur}
                            onKeyDown={handleCellKeyDown}
                            fullWidth
                            multiline
                            maxRows={4}
                            variant="outlined"
                            sx={{
                              "& .MuiOutlinedInput-root": {
                                fontSize: "0.875rem",
                              },
                            }}
                          />
                        ) : (
                          <Tooltip
                            title={value.length > 100 ? value : ""}
                            placement="top"
                          >
                            <Box
                              onClick={() =>
                                handleCellClick(row.id, column, value)
                              }
                              sx={{
                                cursor: "pointer",
                                p: 0.5,
                                borderRadius: 1,
                                "&:hover": {
                                  bgcolor: "action.hover",
                                },
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                                maxWidth: 300,
                              }}
                            >
                              <Typography variant="body2" noWrap>
                                {value || (
                                  <Typography
                                    component="span"
                                    variant="body2"
                                    color="text.secondary"
                                    fontStyle="italic"
                                  >
                                    Click to edit
                                  </Typography>
                                )}
                              </Typography>
                            </Box>
                          </Tooltip>
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </TableContainer>
    </Box>
  );
};
