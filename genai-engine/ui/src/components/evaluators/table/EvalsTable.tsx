import DeleteIcon from "@mui/icons-material/Delete";
import Box from "@mui/material/Box";
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
import React, { useCallback, useMemo, useState } from "react";

import type { EvalsTableProps } from "../types";

import { DeleteConfirmDialog } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { formatDateInTimezone } from "@/utils/formatters";

type SortableColumn = "name" | "created_at" | "latest_version_created_at";

const EvalsTable = ({ evals, sortColumn, sortDirection, onSort, onExpandToFullScreen, onDelete, loading = false }: EvalsTableProps) => {
  const { timezone, use24Hour } = useDisplaySettings();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [evalToDelete, setEvalToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSort = useCallback(
    (column: SortableColumn) => {
      onSort(column);
    },
    [onSort]
  );

  const handleRowClick = useCallback(
    (evalName: string) => {
      onExpandToFullScreen(evalName);
    },
    [onExpandToFullScreen]
  );

  const handleDeleteClick = useCallback((e: React.MouseEvent, evalName: string) => {
    e.stopPropagation();
    setEvalToDelete(evalName);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!evalToDelete || !onDelete) return;

    try {
      setIsDeleting(true);
      await onDelete(evalToDelete);
      setDeleteDialogOpen(false);
      setEvalToDelete(null);
    } catch (err) {
      console.error("Failed to delete eval:", err);
    } finally {
      setIsDeleting(false);
    }
  }, [evalToDelete, onDelete]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setEvalToDelete(null);
  }, []);

  const sortedEvals = useMemo(() => {
    if (!sortColumn) return evals;

    return [...evals].sort((a, b) => {
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
  }, [evals, sortColumn, sortDirection]);

  return (
    <>
      <TableContainer component={Paper} elevation={1}>
        {loading && <LinearProgress />}
        <Table sx={{ minWidth: 650 }} aria-label="evals table" stickyHeader>
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
                  active={sortColumn === "latest_version_created_at"}
                  direction={sortColumn === "latest_version_created_at" ? sortDirection : "asc"}
                  onClick={() => handleSort("latest_version_created_at")}
                  sx={{ width: "100%" }}
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
            {sortedEvals.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ textAlign: "center", py: 6, color: "text.secondary" }}>
                  No evaluators found.
                </TableCell>
              </TableRow>
            )}
            {sortedEvals.map((evalMetadata) => {
              return (
                <TableRow key={evalMetadata.name} hover onClick={() => handleRowClick(evalMetadata.name)} sx={{ cursor: "pointer" }}>
                  <TableCell component="th" scope="row">
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Box sx={{ fontWeight: 500 }}>{evalMetadata.name}</Box>
                      {evalMetadata.versions > 0 && (
                        <Chip
                          label={`v${evalMetadata.versions}`}
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
                  <TableCell>{formatDateInTimezone(evalMetadata.created_at, timezone, { hour12: !use24Hour })}</TableCell>
                  <TableCell>{formatDateInTimezone(evalMetadata.latest_version_created_at, timezone, { hour12: !use24Hour })}</TableCell>
                  <TableCell>{evalMetadata.versions}</TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={(e) => handleDeleteClick(e, evalMetadata.name)}
                      sx={{ color: "error.main" }}
                      aria-label="Delete eval"
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

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Evaluator?"
        description={
          <>
            Are you sure you want to delete <strong>{evalToDelete}</strong>?
          </>
        }
        warningText="This will permanently delete the evaluator and its entire version history. This action cannot be undone."
        isDeleting={isDeleting}
      />
    </>
  );
};

export default EvalsTable;
