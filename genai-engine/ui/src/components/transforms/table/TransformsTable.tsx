import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, IconButton, Box, Tooltip, TableSortLabel, Paper } from "@mui/material";
import LinearProgress from "@mui/material/LinearProgress";
import React from "react";

import { TransformsTableProps } from "../types";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { formatDateInTimezone } from "@/utils/formatters";

export const TransformsTable: React.FC<TransformsTableProps> = ({
  transforms,
  sortColumn,
  sortDirection,
  onSort,
  onView,
  onEdit,
  onDelete,
  loading = false,
}) => {
  const { timezone, use24Hour } = useDisplaySettings();

  const handleSort = (column: string) => {
    onSort(column);
  };

  return (
    <TableContainer component={Paper} elevation={1}>
      {loading && <LinearProgress />}
      <Table stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "name"}
                direction={sortColumn === "name" ? sortDirection : "asc"}
                onClick={() => handleSort("name")}
                sx={{ width: "100%" }}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Name
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Description
              </Box>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "created_at"}
                direction={sortColumn === "created_at" ? sortDirection : "asc"}
                onClick={() => handleSort("created_at")}
                sx={{ width: "100%" }}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Created At
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "updated_at"}
                direction={sortColumn === "updated_at" ? sortDirection : "asc"}
                onClick={() => handleSort("updated_at")}
                sx={{ width: "100%" }}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Updated At
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell align="center">
              <Box component="span" sx={{ fontWeight: 600 }}>
                Actions
              </Box>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {transforms.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} sx={{ textAlign: "center", py: 6, color: "text.secondary" }}>
                No transforms found.
              </TableCell>
            </TableRow>
          )}
          {transforms.map((transform) => (
            <TableRow
              key={transform.id}
              hover
              onClick={() => onView(transform)}
              sx={{ cursor: "pointer" }}
            >
              <TableCell>{transform.name}</TableCell>
              <TableCell>
                <Box
                  sx={{
                    maxWidth: 300,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {transform.description || <em style={{ color: "inherit", opacity: 0.5 }}>No description</em>}
                </Box>
              </TableCell>
              <TableCell>{formatDateInTimezone(transform.created_at, timezone, { hour12: !use24Hour })}</TableCell>
              <TableCell>{formatDateInTimezone(transform.updated_at, timezone, { hour12: !use24Hour })}</TableCell>
              <TableCell align="center">
                <Box sx={{ display: "flex", gap: 0.5, justifyContent: "center" }} onClick={(e) => e.stopPropagation()}>
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => onEdit(transform)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); onDelete(transform.id); }} color="error">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default TransformsTable;
