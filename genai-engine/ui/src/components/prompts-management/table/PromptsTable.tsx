import DeleteIcon from "@mui/icons-material/Delete";
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
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TableSortLabel from "@mui/material/TableSortLabel";
import React, { useCallback, useMemo, useState } from "react";

import type { PromptsTableProps } from "../types";

import { formatDate } from "@/utils/formatters";

type SortableColumn = "name" | "created_at" | "latest_version_created_at";

const PromptsTable = ({ prompts, sortColumn, sortDirection, onSort, onExpandToFullScreen, onDelete }: PromptsTableProps) => {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [promptToDelete, setPromptToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSort = useCallback(
    (column: SortableColumn) => {
      onSort(column);
    },
    [onSort]
  );

  const handleRowClick = useCallback(
    (promptName: string) => {
      onExpandToFullScreen(promptName);
    },
    [onExpandToFullScreen]
  );

  const handleDeleteClick = useCallback(
    (e: React.MouseEvent, promptName: string) => {
      e.stopPropagation();
      setPromptToDelete(promptName);
      setDeleteDialogOpen(true);
    },
    []
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!promptToDelete || !onDelete) return;

    try {
      setIsDeleting(true);
      await onDelete(promptToDelete);
      setDeleteDialogOpen(false);
      setPromptToDelete(null);
    } catch (err) {
      console.error("Failed to delete prompt:", err);
    } finally {
      setIsDeleting(false);
    }
  }, [promptToDelete, onDelete]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setPromptToDelete(null);
  }, []);

  const sortedPrompts = useMemo(() => {
    if (!sortColumn) return prompts;

    return [...prompts].sort((a, b) => {
      let aValue: string | number;
      let bValue: string | number;

      switch (sortColumn) {
        case "name":
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        case "created_at":
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case "latest_version_created_at":
          aValue = new Date(a.latest_version_created_at).getTime();
          bValue = new Date(b.latest_version_created_at).getTime();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === "asc" ? -1 : 1;
      if (aValue > bValue) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }, [prompts, sortColumn, sortDirection]);

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
      <Table sx={{ minWidth: 650 }} aria-label="prompts table" stickyHeader>
        <TableHead>
          <TableRow>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Name
              </Box>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "created_at"}
                direction={sortColumn === "created_at" ? sortDirection : "asc"}
                onClick={() => handleSort("created_at")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Created At
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortColumn === "latest_version_created_at"}
                direction={sortColumn === "latest_version_created_at" ? sortDirection : "asc"}
                onClick={() => handleSort("latest_version_created_at")}
              >
                <Box component="span" sx={{ fontWeight: 600 }}>
                  Latest Version Created At
                </Box>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Versions
              </Box>
            </TableCell>
            <TableCell>
              <Box component="span" sx={{ fontWeight: 600 }}>
                Actions
              </Box>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedPrompts.map((promptMetadata) => {
            return (
              <TableRow
                key={promptMetadata.name}
                hover
                onClick={() => handleRowClick(promptMetadata.name)}
                sx={{
                  cursor: "pointer",
                  "&:hover": {
                    backgroundColor: "action.hover",
                  },
                }}
              >
                <TableCell component="th" scope="row">
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Box sx={{ fontWeight: 500 }}>{promptMetadata.name}</Box>
                    {promptMetadata.versions > 0 && (
                      <Chip
                        label={`v${promptMetadata.versions}`}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: "0.75rem",
                          fontWeight: 500,
                        }}
                      />
                    )}
                  </Box>
                </TableCell>
                <TableCell>{formatDate(promptMetadata.created_at)}</TableCell>
                <TableCell>{formatDate(promptMetadata.latest_version_created_at)}</TableCell>
                <TableCell>{promptMetadata.versions}</TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={(e) => handleDeleteClick(e, promptMetadata.name)}
                    sx={{ color: "error.main" }}
                    aria-label="Delete prompt"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
      </TableContainer>

      <Dialog
      open={deleteDialogOpen}
      onClose={handleDeleteCancel}
      aria-labelledby="delete-dialog-title"
      aria-describedby="delete-dialog-description"
    >
      <DialogTitle id="delete-dialog-title">Delete Prompt?</DialogTitle>
      <DialogContent>
        <DialogContentText id="delete-dialog-description">
          Are you sure you want to delete <strong>{promptToDelete}</strong>?
        </DialogContentText>
        <Box
          sx={{ mt: 2, p: 2, bgcolor: "warning.lighter", borderRadius: 1 }}
        >
          <strong>Warning:</strong> This will permanently delete the prompt
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

export default PromptsTable;
