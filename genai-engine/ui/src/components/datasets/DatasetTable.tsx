import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import FormatColorFillIcon from "@mui/icons-material/FormatColorFill";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import {
  Alert,
  Box,
  CircularProgress,
  Divider,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
} from "@mui/material";
import React, { useState } from "react";

import { DatasetTableRow } from "./DatasetTableRow";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface DatasetTableProps {
  datasetId: string;
  columns: string[];
  rows: DatasetVersionRowResponse[];
  isLoading: boolean;
  error?: Error | null;
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onEditRow: (row: DatasetVersionRowResponse) => void;
  onDeleteRow: (rowId: string) => void;
  onFillColumn?: (columnName: string) => void;
  emptyMessage?: string;
  searchQuery?: string;
}

interface ColumnMenuState {
  anchorEl: HTMLElement | null;
  column: string | null;
}

export const DatasetTable: React.FC<DatasetTableProps> = ({
  datasetId,
  columns,
  rows,
  isLoading,
  error,
  sortColumn,
  sortDirection,
  onSort,
  onEditRow,
  onDeleteRow,
  onFillColumn,
  emptyMessage,
  searchQuery,
}) => {
  const [menuState, setMenuState] = useState<ColumnMenuState>({
    anchorEl: null,
    column: null,
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, column: string) => {
    event.stopPropagation();
    setMenuState({ anchorEl: event.currentTarget, column });
  };

  const handleMenuClose = () => {
    setMenuState({ anchorEl: null, column: null });
  };

  const handleSortAsc = () => {
    if (menuState.column) {
      if (sortColumn === menuState.column && sortDirection === "asc") {
        // Already sorted ascending, do nothing or toggle off
      } else {
        onSort(menuState.column);
        if (sortDirection === "desc") {
          onSort(menuState.column); // Toggle to asc
        }
      }
    }
    handleMenuClose();
  };

  const handleSortDesc = () => {
    if (menuState.column) {
      if (sortColumn !== menuState.column) {
        onSort(menuState.column); // First click sets asc
      }
      if (sortDirection === "asc") {
        onSort(menuState.column); // Second click sets desc
      }
    }
    handleMenuClose();
  };

  const handleFillColumn = () => {
    if (menuState.column && onFillColumn) {
      onFillColumn(menuState.column);
    }
    handleMenuClose();
  };

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error.message || "Failed to load dataset version"}</Alert>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        overflow: "auto",
        minHeight: 0,
        backgroundColor: "background.paper",
      }}
    >
      <Table size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell
                key={column}
                sx={{
                  fontWeight: 600,
                  minWidth: 150,
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <TableSortLabel
                    active={sortColumn === column}
                    direction={sortColumn === column ? sortDirection : "asc"}
                    onClick={() => onSort(column)}
                  >
                    {column}
                  </TableSortLabel>
                  <IconButton size="small" onClick={(e) => handleMenuOpen(e, column)} sx={{ ml: 0.5, p: 0.25 }}>
                    <MoreVertIcon fontSize="small" />
                  </IconButton>
                </Box>
              </TableCell>
            ))}
            <TableCell
              sx={{
                fontWeight: 600,
                minWidth: 100,
                textAlign: "center",
                position: "sticky",
                right: 0,
                zIndex: 3,
                boxShadow: (theme) => (theme.palette.mode === "dark" ? "-2px 0 4px rgba(0, 0, 0, 0.3)" : "-2px 0 4px rgba(0, 0, 0, 0.1)"),
              }}
            >
              Actions
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={columns.length + 1} align="center">
                <CircularProgress size={24} sx={{ my: 2 }} />
              </TableCell>
            </TableRow>
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length + 1} align="center" sx={{ py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  {searchQuery ? "No matching rows" : emptyMessage || "No data yet. Click 'Add Row' to get started."}
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <DatasetTableRow key={row.id} row={row} columns={columns} onEdit={onEditRow} onDelete={onDeleteRow} datasetId={datasetId} />
            ))
          )}
        </TableBody>
      </Table>

      {/* Column Actions Menu */}
      <Menu
        anchorEl={menuState.anchorEl}
        open={Boolean(menuState.anchorEl)}
        onClose={handleMenuClose}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "right",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "right",
        }}
      >
        <MenuItem onClick={handleSortAsc}>
          <ListItemIcon>
            <ArrowUpwardIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Sort Ascending</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleSortDesc}>
          <ListItemIcon>
            <ArrowDownwardIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Sort Descending</ListItemText>
        </MenuItem>
        {onFillColumn && <Divider />}
        {onFillColumn && (
          <MenuItem onClick={handleFillColumn}>
            <ListItemIcon>
              <FormatColorFillIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Fill All Rows...</ListItemText>
          </MenuItem>
        )}
      </Menu>
    </Box>
  );
};
