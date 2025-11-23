import DeleteIcon from "@mui/icons-material/Delete";
import LaunchIcon from "@mui/icons-material/Launch";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import IconButton from "@mui/material/IconButton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

import type { NotebooksTableProps } from "./types";

const NotebooksTable: React.FC<NotebooksTableProps> = ({
  notebooks,
  sortColumn,
  sortDirection,
  onSort,
  onRowClick,
  onLaunchNotebook,
  onDelete,
}) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [notebookToDelete, setNotebookToDelete] = useState<any>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteClick = (notebook: any, event: React.MouseEvent) => {
    event.stopPropagation();
    setNotebookToDelete(notebook);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!notebookToDelete) return;

    setIsDeleting(true);
    try {
      await onDelete(notebookToDelete.id);
      setDeleteDialogOpen(false);
      setNotebookToDelete(null);
    } catch (error) {
      console.error("Failed to delete notebook:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setNotebookToDelete(null);
  };

  const getStatusChipSx = (status: string | undefined) => {
    if (!status) return {};

    const colorMap: Record<string, any> = {
      queued: { color: "text.secondary", borderColor: "text.secondary" },
      running: { color: "primary.main", borderColor: "primary.main" },
      evaluating: { color: "info.main", borderColor: "info.main" },
      completed: { color: "success.main", borderColor: "success.main" },
      failed: { color: "error.main", borderColor: "error.main" },
    };

    const colors = colorMap[status] || colorMap.queued;
    return {
      backgroundColor: "transparent",
      color: colors.color,
      borderColor: colors.borderColor,
      borderWidth: 1,
      borderStyle: "solid",
      textTransform: "capitalize",
    };
  };

  return (
    <>
      <TableContainer sx={{ height: "100%" }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "name"}
                  direction={sortColumn === "name" ? sortDirection : "asc"}
                  onClick={() => onSort("name")}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Name
                  </Typography>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Description
                </Typography>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "run_count"}
                  direction={sortColumn === "run_count" ? sortDirection : "desc"}
                  onClick={() => onSort("run_count")}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Runs
                  </Typography>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Latest Run
                </Typography>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "updated_at"}
                  direction={sortColumn === "updated_at" ? sortDirection : "desc"}
                  onClick={() => onSort("updated_at")}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Updated
                  </Typography>
                </TableSortLabel>
              </TableCell>
              <TableCell align="right">
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Actions
                </Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {notebooks.map((notebook) => (
              <TableRow
                key={notebook.id}
                hover
                onClick={() => onRowClick(notebook.id)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {notebook.name}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400 }}>
                    {notebook.description || "—"}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{notebook.run_count}</Typography>
                </TableCell>
                <TableCell>
                  {notebook.latest_run_status ? (
                    <Chip
                      label={notebook.latest_run_status}
                      size="small"
                      sx={getStatusChipSx(notebook.latest_run_status)}
                    />
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      No runs
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="body2" color="text.secondary">
                    {new Date(notebook.updated_at).toLocaleString()}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                    <Tooltip title="Launch Notebook">
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<LaunchIcon />}
                        onClick={(e) => {
                          e.stopPropagation();
                          onLaunchNotebook(notebook.id);
                        }}
                      >
                        Launch
                      </Button>
                    </Tooltip>
                    <Tooltip title="Delete Notebook">
                      <IconButton
                        size="small"
                        onClick={(e) => handleDeleteClick(notebook, e)}
                        color="error"
                      >
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

      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-notebook-dialog-title"
        aria-describedby="delete-notebook-dialog-description"
      >
        <DialogTitle id="delete-notebook-dialog-title">Delete Notebook?</DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-notebook-dialog-description">
            Are you sure you want to delete <strong>{notebookToDelete?.name}</strong>?
          </DialogContentText>
          <Box sx={{ mt: 2, p: 2, bgcolor: "info.lighter", borderRadius: 1 }}>
            <strong>Note:</strong> Experiments created from this notebook will be preserved but will no longer be linked to the notebook.
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

export default NotebooksTable;

