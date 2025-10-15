import React, { useCallback, useState } from "react";
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
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import { Dataset, SortField, SortOrder } from "@/types/dataset";

interface DatasetsTableProps {
  datasets: Dataset[];
  sortBy: SortField;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  onRowClick: (dataset: Dataset) => void;
  onDelete?: (datasetId: string) => Promise<void>;
}

export const DatasetsTable: React.FC<DatasetsTableProps> = ({
  datasets,
  sortBy,
  sortOrder,
  onSort,
  onRowClick,
  onDelete,
}) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [datasetToDelete, setDatasetToDelete] = useState<Dataset | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const formatDate = useCallback((dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateString;
    }
  }, []);

  const formatNumber = useCallback((num: number): string => {
    return num.toLocaleString();
  }, []);

  const createSortHandler = useCallback(
    (field: SortField) => () => {
      onSort(field);
    },
    [onSort]
  );

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
      // Error is handled in parent component
    } finally {
      setIsDeleting(false);
    }
  }, [datasetToDelete, onDelete]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setDatasetToDelete(null);
  }, []);

  return (
    <TableContainer component={Paper} elevation={1}>
      <Table sx={{ minWidth: 650 }} aria-label="datasets table">
        <TableHead>
          <TableRow>
            <TableCell>
              <TableSortLabel
                active={sortBy === "name"}
                direction={sortBy === "name" ? sortOrder : "asc"}
                onClick={createSortHandler("name")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Dataset Name
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell align="right">
              <TableSortLabel
                active={sortBy === "rowCount"}
                direction={sortBy === "rowCount" ? sortOrder : "asc"}
                onClick={createSortHandler("rowCount")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Rows
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell align="right">
              <Box component="span" sx={{ fontWeight: 600 }}>
                Columns
              </Box>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortBy === "createdAt"}
                direction={sortBy === "createdAt" ? sortOrder : "asc"}
                onClick={createSortHandler("createdAt")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Created At
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortBy === "lastModified"}
                direction={sortBy === "lastModified" ? sortOrder : "asc"}
                onClick={createSortHandler("lastModified")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Last Modified
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Created By
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
                <Box sx={{ fontWeight: 500 }}>{dataset.name}</Box>
              </TableCell>
              <TableCell align="right">
                {formatNumber(dataset.rowCount)}
              </TableCell>
              <TableCell align="right">{dataset.columnCount}</TableCell>
              <TableCell>{formatDate(dataset.createdAt)}</TableCell>
              <TableCell>{formatDate(dataset.lastModified)}</TableCell>
              <TableCell>{dataset.owner}</TableCell>
              <TableCell align="center">
                <Box
                  sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}
                >
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

      {/* Delete Confirmation Dialog */}
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
            <Box
              sx={{ mt: 2, p: 2, bgcolor: "warning.lighter", borderRadius: 1 }}
            >
              <strong>Warning:</strong> This will permanently delete the dataset
              and its entire version history. This action cannot be undone.
            </Box>
          </DialogContentText>
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
    </TableContainer>
  );
};
