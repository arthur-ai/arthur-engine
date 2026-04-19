import DeleteIcon from "@mui/icons-material/Delete";
import HistoryIcon from "@mui/icons-material/History";
import LaunchIcon from "@mui/icons-material/Launch";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
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

import type { RagNotebooksTableProps } from "./types";

import { DeleteConfirmDialog } from "@/components/common";
import type { RagNotebookSummary } from "@/lib/api-client/api-client";
import { getStatusChipSx } from "@/utils/statusChipStyles";

const RagNotebooksTable: React.FC<RagNotebooksTableProps> = ({
  notebooks,
  sortColumn,
  sortDirection,
  onSort,
  onRowClick,
  onLaunchNotebook,
  onViewLastRun,
  onDelete,
  loading = false,
}) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [notebookToDelete, setNotebookToDelete] = useState<RagNotebookSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteClick = (notebook: RagNotebookSummary, event: React.MouseEvent) => {
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
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setNotebookToDelete(null);
  };

  return (
    <>
      <TableContainer component={Paper} elevation={1}>
        {loading && <LinearProgress />}
        <Table stickyHeader>
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
                  active={sortColumn === "run_count"}
                  direction={sortColumn === "run_count" ? sortDirection : "desc"}
                  onClick={() => onSort("run_count")}
                  sx={{ width: "100%" }}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Runs
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortColumn === "latest_run_status"}
                  direction={sortColumn === "latest_run_status" ? sortDirection : "asc"}
                  onClick={() => onSort("latest_run_status")}
                  sx={{ width: "100%" }}
                >
                  <Box component="span" sx={{ fontWeight: 600 }}>
                    Latest Run
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
                    Updated
                  </Box>
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Actions
                </Box>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {notebooks.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} sx={{ textAlign: "center", py: 6, color: "text.secondary" }}>
                  No notebooks found.
                </TableCell>
              </TableRow>
            )}
            {notebooks.map((notebook) => (
              <TableRow key={notebook.id} hover onClick={() => onRowClick(notebook.id)} sx={{ cursor: "pointer" }}>
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
                    <Chip label={notebook.latest_run_status} size="small" sx={getStatusChipSx(notebook.latest_run_status)} />
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
                <TableCell>
                  <Box sx={{ display: "flex", gap: 1 }}>
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
                    <Tooltip title={notebook.latest_run_id ? "View last run" : "No runs yet"}>
                      <span>
                        <IconButton
                          size="small"
                          disabled={!notebook.latest_run_id}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (notebook.latest_run_id) onViewLastRun(notebook.latest_run_id);
                          }}
                        >
                          <HistoryIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Delete Notebook">
                      <IconButton size="small" onClick={(e) => handleDeleteClick(notebook, e)} color="error">
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

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete RAG Notebook?"
        description={
          <>
            Are you sure you want to delete <strong>{notebookToDelete?.name}</strong>?
          </>
        }
        noteText="Experiments created from this notebook will be preserved but will no longer be linked to the notebook."
        isDeleting={isDeleting}
      />
    </>
  );
};

export default RagNotebooksTable;
