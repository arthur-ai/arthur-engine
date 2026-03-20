import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { Box, IconButton, TableCell, TableRow } from "@mui/material";
import React from "react";

import { CopyableChip } from "@/components/common/CopyableChip";

import { DatasetTableCell } from "./DatasetTableCell";

import { DatasetVersionRowResponse } from "@/lib/api-client/api-client";

interface DatasetTableRowProps {
  row: DatasetVersionRowResponse;
  columns: string[];
  onEdit: (row: DatasetVersionRowResponse) => void;
  onDelete: (rowId: string) => void;
  datasetId: string;
}

export const DatasetTableRow: React.FC<DatasetTableRowProps> = React.memo(({ row, columns, onEdit, onDelete, datasetId }) => {
  return (
    <TableRow hover>
      <TableCell
        sx={{
          position: "sticky",
          left: 0,
          backgroundColor: "background.paper",
          zIndex: 1,
          boxShadow: (theme) => (theme.palette.mode === "dark" ? "2px 0 4px rgba(0, 0, 0, 0.3)" : "2px 0 4px rgba(0, 0, 0, 0.1)"),
        }}
      >
        <CopyableChip label={row.id} size="small" sx={{ maxWidth: 120, "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" } }} />
      </TableCell>
      {columns.map((column) => {
        const columnData = row.data.find((col) => col.column_name === column);
        const value = columnData?.column_value;

        return <DatasetTableCell key={column} value={value} columnName={column} datasetId={datasetId} />;
      })}
      <TableCell
        sx={{
          textAlign: "center",
          position: "sticky",
          right: 0,
          backgroundColor: "background.paper",
          zIndex: 1,
          boxShadow: (theme) => (theme.palette.mode === "dark" ? "-2px 0 4px rgba(0, 0, 0, 0.3)" : "-2px 0 4px rgba(0, 0, 0, 0.1)"),
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
});
