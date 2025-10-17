import {
  Alert,
  Box,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TableSortLabel,
  Typography,
} from "@mui/material";
import React from "react";

import { DatasetTableRow } from "./DatasetTableRow";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface DatasetTableProps {
  columns: string[];
  rows: DatasetVersionRowResponse[];
  isLoading: boolean;
  error?: Error | null;
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onEditRow: (row: DatasetVersionRowResponse) => void;
  onDeleteRow: (rowId: string) => void;
  emptyMessage?: string;
  searchQuery?: string;
}

export const DatasetTable: React.FC<DatasetTableProps> = ({
  columns,
  rows,
  isLoading,
  error,
  sortColumn,
  sortDirection,
  onSort,
  onEditRow,
  onDeleteRow,
  emptyMessage,
  searchQuery,
}) => {
  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          {error.message || "Failed to load dataset version"}
        </Alert>
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
            <TableCell
              sx={{
                fontWeight: 600,
                minWidth: 100,
                backgroundColor: "grey.100",
              }}
            >
              Row ID
            </TableCell>
            {columns.map((column) => (
              <TableCell
                key={column}
                sx={{
                  fontWeight: 600,
                  minWidth: 150,
                  backgroundColor: "grey.100",
                }}
              >
                <TableSortLabel
                  active={sortColumn === column}
                  direction={sortColumn === column ? sortDirection : "asc"}
                  onClick={() => onSort(column)}
                >
                  {column}
                </TableSortLabel>
              </TableCell>
            ))}
            <TableCell
              sx={{
                fontWeight: 600,
                minWidth: 100,
                backgroundColor: "grey.100",
                textAlign: "center",
              }}
            >
              Actions
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell colSpan={columns.length + 2} align="center">
                <CircularProgress size={24} sx={{ my: 2 }} />
              </TableCell>
            </TableRow>
          ) : rows.length === 0 ? (
            <TableRow>
              <TableCell
                colSpan={columns.length + 2}
                align="center"
                sx={{ py: 4 }}
              >
                <Typography variant="body2" color="text.secondary">
                  {searchQuery
                    ? "No matching rows"
                    : emptyMessage ||
                      "No data yet. Click 'Add Row' to get started."}
                </Typography>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <DatasetTableRow
                key={row.id}
                row={row}
                columns={columns}
                onEdit={onEditRow}
                onDelete={onDeleteRow}
              />
            ))
          )}
        </TableBody>
      </Table>
    </Box>
  );
};
