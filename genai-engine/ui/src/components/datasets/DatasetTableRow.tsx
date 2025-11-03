import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { Box, IconButton, TableCell, TableRow } from "@mui/material";
import React from "react";

import { DatasetTableCell } from "./DatasetTableCell";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface DatasetTableRowProps {
  row: DatasetVersionRowResponse;
  columns: string[];
  onEdit: (row: DatasetVersionRowResponse) => void;
  onDelete: (rowId: string) => void;
}

export const DatasetTableRow: React.FC<DatasetTableRowProps> = React.memo(
  ({ row, columns, onEdit, onDelete }) => {
    return (
      <TableRow hover>
        {columns.map((column) => {
          const columnData = row.data.find((col) => col.column_name === column);
          const value = columnData?.column_value;

          return (
            <DatasetTableCell key={column} value={value} columnName={column} />
          );
        })}
        <TableCell
          sx={{
            textAlign: "center",
            position: "sticky",
            right: 0,
            backgroundColor: "background.paper",
            zIndex: 1,
            boxShadow: "-2px 0 4px rgba(0, 0, 0, 0.1)",
          }}
        >
          <Box
            sx={{
              display: "flex",
              gap: 0.5,
              justifyContent: "center",
            }}
          >
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onEdit(row);
              }}
              sx={{ color: "primary.main" }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(row.id);
              }}
              sx={{ color: "error.main" }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Box>
        </TableCell>
      </TableRow>
    );
  }
);
