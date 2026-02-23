import { Add, Delete, Lock, LockOpen } from "@mui/icons-material";
import {
  Box,
  Button,
  Checkbox,
  IconButton,
  Paper,
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
  selectedRows: Set<string>;
  onSelectedRowsChange: (selectedRows: Set<string>) => void;
  onUpdateRow: (id: string, data: Record<string, string>) => void;
  onAddRow: (data: Record<string, string>) => void;
  onDeleteRows: (ids: string[]) => void;
  onToggleLock: (id: string) => void;
}

export const SyntheticDataTable: React.FC<SyntheticDataTableProps> = ({
  rows,
  columns,
  selectedRows,
  onSelectedRowsChange,
  onUpdateRow,
  onAddRow,
  onDeleteRows,
  onToggleLock,
}) => {
  const [editingCell, setEditingCell] = useState<{
    rowId: string;
    column: string;
  } | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (checked) {
        // Only select unlocked rows
        onSelectedRowsChange(new Set(rows.filter((r) => !r.locked).map((r) => r.id)));
      } else {
        onSelectedRowsChange(new Set());
      }
    },
    [rows, onSelectedRowsChange]
  );

  const handleSelectRow = useCallback(
    (rowId: string, checked: boolean) => {
      const next = new Set(selectedRows);
      if (checked) {
        next.add(rowId);
      } else {
        next.delete(rowId);
      }
      onSelectedRowsChange(next);
    },
    [selectedRows, onSelectedRowsChange]
  );

  const handleDeleteSelected = useCallback(() => {
    onDeleteRows(Array.from(selectedRows));
    onSelectedRowsChange(new Set());
  }, [selectedRows, onDeleteRows, onSelectedRowsChange]);

  const handleCellClick = useCallback((rowId: string, column: string, currentValue: string, isLocked: boolean) => {
    // Prevent editing locked rows
    if (isLocked) return;

    setEditingCell({ rowId, column });
    setEditValue(currentValue);
  }, []);

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

  const unlockedRows = rows.filter((r) => !r.locked);
  const unlockedSelectedCount = unlockedRows.filter((r) => selectedRows.has(r.id)).length;
  const allSelected = unlockedRows.length > 0 && unlockedSelectedCount === unlockedRows.length;
  const someSelected = unlockedSelectedCount > 0 && unlockedSelectedCount < unlockedRows.length;

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
            <Button size="small" color="error" startIcon={<Delete />} onClick={handleDeleteSelected}>
              Delete ({selectedRows.size})
            </Button>
          )}
          <Button size="small" startIcon={<Add />} onClick={handleAddRow}>
            Add Row
          </Button>
        </Box>
      </Box>

      {/* Table */}
      <TableContainer component={Paper} elevation={1} sx={{ flex: 1, overflow: "auto" }}>
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
            <Typography variant="body2">No data generated yet. Use the chat to generate or refine data.</Typography>
          </Box>
        ) : (
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.100") }}>
                  <Checkbox checked={allSelected} indeterminate={someSelected} onChange={(e) => handleSelectAll(e.target.checked)} />
                </TableCell>
                <TableCell
                  sx={{
                    fontWeight: "bold",
                    bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.100"),
                    width: 60,
                  }}
                >
                  Lock
                </TableCell>
                {columns.map((column) => (
                  <TableCell
                    key={column}
                    sx={{
                      fontWeight: "bold",
                      bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.100"),
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
                    bgcolor: (theme) =>
                      row.locked
                        ? theme.palette.mode === "dark"
                          ? "grey.800"
                          : "grey.100"
                        : row.status === "added"
                          ? "success.50"
                          : row.status === "modified"
                            ? "warning.50"
                            : "inherit",
                    opacity: row.locked ? 0.7 : 1,
                  }}
                >
                  <TableCell padding="checkbox">
                    <Checkbox checked={selectedRows.has(row.id)} onChange={(e) => handleSelectRow(row.id, e.target.checked)} disabled={row.locked} />
                  </TableCell>
                  <TableCell>
                    <Tooltip title={row.locked ? "Unlock row" : "Lock row"}>
                      <IconButton size="small" onClick={() => onToggleLock(row.id)} color={row.locked ? "primary" : "default"}>
                        {row.locked ? <Lock fontSize="small" /> : <LockOpen fontSize="small" />}
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                  {columns.map((column) => {
                    const isEditing = editingCell?.rowId === row.id && editingCell?.column === column;
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
                          <Tooltip title={row.locked ? "Unlock row to edit" : value.length > 100 ? value : ""} placement="top">
                            <Box
                              onClick={() => handleCellClick(row.id, column, value, !!row.locked)}
                              sx={{
                                cursor: row.locked ? "not-allowed" : "pointer",
                                p: 0.5,
                                borderRadius: 1,
                                "&:hover": {
                                  bgcolor: row.locked ? "transparent" : "action.hover",
                                },
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                                maxWidth: 300,
                              }}
                            >
                              <Typography variant="body2" noWrap>
                                {value || (
                                  <Typography component="span" variant="body2" color="text.secondary" fontStyle="italic">
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
