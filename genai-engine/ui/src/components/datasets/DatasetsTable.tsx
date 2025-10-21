import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Paper,
  Box,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  CircularProgress,
  Chip,
} from "@mui/material";
import React, { useCallback, useState } from "react";

import { Dataset, SortOrder } from "@/types/dataset";

interface DatasetsTableProps {
  datasets: Dataset[];
  sortOrder: SortOrder;
  onSort: () => void;
  onRowClick: (dataset: Dataset) => void;
  onEdit?: (dataset: Dataset) => void;
  onDelete?: (datasetId: string) => Promise<void>;
}

export const DatasetsTable: React.FC<DatasetsTableProps> = ({
  datasets,
  sortOrder,
  onSort,
  onRowClick,
  onEdit,
  onDelete,
}) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [datasetToDelete, setDatasetToDelete] = useState<Dataset | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const formatDate = useCallback((timestamp: number): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return String(timestamp);
    }
  }, []);

  const handleDeleteClick = useCallback(
    (e: React.MouseEvent, dataset: Dataset) => {
      e.stopPropagation();
      setDatasetToDelete(dataset);
      setDeleteDialogOpen(true);
    },
    []
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!datasetToDelete || !onDelete) return;

    try {
      setIsDeleting(true);
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

  return (
    <>
      <TableContainer
        component={Paper}
        elevation={1}
        sx={{
          overflow: "auto",
          height: "100%",
        }}
      >
        <Table sx={{ minWidth: 650 }} aria-label="datasets table" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Dataset Name
                </Box>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={true}
                  direction={sortOrder}
                  onClick={onSort}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Last Modified
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Created At
                </Box>
              </TableCell>
              <TableCell align="center">
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Actions
                </Box>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {datasets.map((dataset) => (
              <TableRow
                key={dataset.id}
                hover
                onClick={() => onRowClick(dataset)}
                sx={{
                  cursor: "pointer",
                  "&:hover": {
                    backgroundColor: "action.hover",
                  },
                }}
              >
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
                    <Box
                      component="span"
                      sx={{ fontSize: "0.875rem", color: "text.secondary" }}
                    >
                      {dataset.description}
                    </Box>
                  )}
                </TableCell>
                <TableCell>{formatDate(dataset.updated_at)}</TableCell>
                <TableCell>{formatDate(dataset.created_at)}</TableCell>
                <TableCell align="center">
                  <Box
                    sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}
                  >
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
                    <IconButton
                      size="small"
                      onClick={(e) => handleDeleteClick(e, dataset)}
                      sx={{ color: "error.main" }}
                      aria-label="Delete dataset"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <DialogTitle id="delete-dialog-title">Delete Dataset?</DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-dialog-description">
            Are you sure you want to delete{" "}
            <strong>{datasetToDelete?.name}</strong>?
          </DialogContentText>
          <Box
            sx={{ mt: 2, p: 2, bgcolor: "warning.lighter", borderRadius: 1 }}
          >
            <strong>Warning:</strong> This will permanently delete the dataset
            and its entire version history. This action cannot be undone.
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={handleDeleteCancel} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={isDeleting}
            startIcon={isDeleting ? <CircularProgress size={16} /> : null}
          >
            {isDeleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
