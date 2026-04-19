import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel, Paper, Box, IconButton, Chip, LinearProgress } from "@mui/material";
import React, { useCallback, useMemo, useState } from "react";

import { DeleteConfirmDialog } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import type { DatasetResponse } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";
import { formatDateInTimezone } from "@/utils/formatters";

interface DatasetsTableProps {
  datasets: DatasetResponse[];
  sortColumn: string | null;
  sortDirection: "asc" | "desc";
  onSort: (column: string) => void;
  onRowClick: (dataset: DatasetResponse) => void;
  onEdit?: (dataset: DatasetResponse) => void;
  onDelete?: (datasetId: string) => Promise<void>;
  loading?: boolean;
}

export const DatasetsTable: React.FC<DatasetsTableProps> = ({ datasets, sortColumn, sortDirection, onSort, onRowClick, onEdit, onDelete, loading = false }) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [datasetToDelete, setDatasetToDelete] = useState<DatasetResponse | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const { timezone, use24Hour } = useDisplaySettings();

  const handleDeleteClick = useCallback((e: React.MouseEvent, dataset: DatasetResponse) => {
    e.stopPropagation();
    setDatasetToDelete(dataset);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!datasetToDelete || !onDelete) return;

    try {
      setIsDeleting(true);
      track(EVENT_NAMES.DATASET_DELETE_CONFIRMED, { dataset_id: datasetToDelete.id });
      await onDelete(datasetToDelete.id);
      setDeleteDialogOpen(false);
      setDatasetToDelete(null);
    } catch (err) {
      console.error("Failed to delete dataset:", err);
    } finally {
      setIsDeleting(false);
    }
  }, [datasetToDelete, onDelete]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setDatasetToDelete(null);
  }, []);

  // Client-side sort for columns the server doesn't sort by (server sorts by updated_at only)
  const sortedDatasets = useMemo(() => {
    if (sortColumn !== "name" && sortColumn !== "created_at") return datasets;
    return [...datasets].sort((a, b) => {
      const aVal = sortColumn === "name" ? a.name.toLowerCase() : new Date(a.created_at).getTime();
      const bVal = sortColumn === "name" ? b.name.toLowerCase() : new Date(b.created_at).getTime();
      if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [datasets, sortColumn, sortDirection]);

  return (
    <>
      <TableContainer component={Paper} elevation={1}>
        {loading && <LinearProgress />}
        <Table sx={{ minWidth: 650 }} aria-label="datasets table" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "name"}
                  direction={sortColumn === "name" ? sortDirection : "asc"}
                  onClick={() => onSort("name")}
                  sx={{ width: "100%" }}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Dataset Name
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "updated_at"}
                  direction={sortColumn === "updated_at" ? sortDirection : "desc"}
                  onClick={() => onSort("updated_at")}
                  sx={{ width: "100%" }}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Last Modified
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "created_at"}
                  direction={sortColumn === "created_at" ? sortDirection : "asc"}
                  onClick={() => onSort("created_at")}
                  sx={{ width: "100%" }}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Created At
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
            {sortedDatasets.length === 0 && (
              <TableRow>
                <TableCell colSpan={4} sx={{ textAlign: "center", py: 6, color: "text.secondary" }}>
                  No datasets found.
                </TableCell>
              </TableRow>
            )}
            {sortedDatasets.map((dataset) => (
              <TableRow key={dataset.id} hover onClick={() => onRowClick(dataset)} sx={{ cursor: "pointer" }}>
                <TableCell component="th" scope="row">
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Box sx={{ fontWeight: 500 }}>{dataset.name}</Box>
                    {dataset.latest_version_number != null && (
                      <Chip
                        label={`v${dataset.latest_version_number}`}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: "0.75rem",
                          fontWeight: 500,
                        }}
                      />
                    )}
                  </Box>
                  {dataset.description && (
                    <Box component="span" sx={{ fontSize: "0.875rem", color: "text.secondary" }}>
                      {dataset.description}
                    </Box>
                  )}
                </TableCell>
                <TableCell>{formatDateInTimezone(dataset.updated_at, timezone, { hour12: !use24Hour })}</TableCell>
                <TableCell>{formatDateInTimezone(dataset.created_at, timezone, { hour12: !use24Hour })}</TableCell>
                <TableCell align="center">
                  <Box sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}>
                    {onEdit && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          onEdit(dataset);
                        }}
                        sx={{ color: "primary.main" }}
                        aria-label="Edit dataset"
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    )}
                    <IconButton size="small" onClick={(e) => handleDeleteClick(e, dataset)} sx={{ color: "error.main" }} aria-label="Delete dataset">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Dataset?"
        description={
          <>
            Are you sure you want to delete <strong>{datasetToDelete?.name}</strong>?
          </>
        }
        warningText="This will permanently delete the dataset and its entire version history. This action cannot be undone."
        isDeleting={isDeleting}
      />
    </>
  );
};
