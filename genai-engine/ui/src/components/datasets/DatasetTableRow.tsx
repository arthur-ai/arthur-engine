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
        <TableCell
          sx={{
            fontFamily: "monospace",
            fontSize: "0.75rem",
            color: "text.secondary",
          }}
        >
          {row.id}
        </TableCell>
        {columns.map((column) => {
          const columnData = row.data.find((col) => col.column_name === column);
          const value = columnData?.column_value;

          return <DatasetTableCell key={column} value={value} />;
        })}
        <TableCell sx={{ textAlign: "center" }}>
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
