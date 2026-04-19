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
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useMemo, useState } from "react";

import type { PromptsTableProps } from "../types";

import { DeleteConfirmDialog } from "@/components/common";
import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { formatDateInTimezone } from "@/utils/formatters";

type SortableColumn = "name" | "created_at" | "latest_version_created_at";

const PromptsTable = ({ prompts, sortColumn, sortDirection, onSort, onExpandToFullScreen, onDelete, loading = false }: PromptsTableProps) => {
  const { timezone, use24Hour } = useDisplaySettings();
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

  const handleDeleteClick = useCallback((e: React.MouseEvent, promptName: string) => {
    e.stopPropagation();
    setPromptToDelete(promptName);
    setDeleteDialogOpen(true);
  }, []);

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
      <TableContainer component={Paper} elevation={1}>
        {loading && <LinearProgress />}
        <Table sx={{ minWidth: 650 }} aria-label="prompts table" stickyHeader>
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
                  Tags
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
            {sortedPrompts.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} sx={{ textAlign: "center", py: 6, color: "text.secondary" }}>
                  No prompts found.
                </TableCell>
              </TableRow>
            )}
            {sortedPrompts.map((promptMetadata) => {
              const tags = promptMetadata.tags ?? [];
              const productionTag = tags.find((tag) => tag.toLowerCase() === "production");
              const otherTags = tags.filter((tag) => tag.toLowerCase() !== "production");
              const displayTags: Array<{ label: string; isProduction: boolean }> = [];
              if (productionTag !== undefined) displayTags.push({ label: productionTag, isProduction: true });
              otherTags.slice(0, 3 - displayTags.length).forEach((tag) => {
                displayTags.push({ label: tag, isProduction: false });
              });
              const displayedLabels = new Set(displayTags.map((d) => d.label));
              const hiddenTags = tags.filter((t) => !displayedLabels.has(t));
              const hiddenTagCount = hiddenTags.length;

              return (
                <TableRow key={promptMetadata.name} hover onClick={() => handleRowClick(promptMetadata.name)} sx={{ cursor: "pointer" }}>
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
                  <TableCell>{formatDateInTimezone(promptMetadata.created_at, timezone, { hour12: !use24Hour })}</TableCell>
                  <TableCell>{formatDateInTimezone(promptMetadata.latest_version_created_at, timezone, { hour12: !use24Hour })}</TableCell>
                  <TableCell>{promptMetadata.versions}</TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                      {displayTags.map((tag) => (
                        <Chip
                          key={tag.label}
                          label={tag.label}
                          size="small"
                          color={tag.isProduction ? "success" : "primary"}
                          variant={tag.isProduction ? "filled" : "outlined"}
                          sx={{ height: 20, fontSize: "0.75rem" }}
                        />
                      ))}
                      {hiddenTagCount > 0 && (
                        <Tooltip title={hiddenTags.join(", ")}>
                          <Chip label={`+${hiddenTagCount}`} size="small" variant="outlined" sx={{ height: 20, fontSize: "0.75rem" }} />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
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

      <DeleteConfirmDialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        onConfirm={handleDeleteConfirm}
        title="Delete Prompt?"
        description={
          <>
            Are you sure you want to delete <strong>{promptToDelete}</strong>?
          </>
        }
        warningText="This will permanently delete the prompt and its entire version history. This action cannot be undone."
        isDeleting={isDeleting}
      />
    </>
  );
};

export default PromptsTable;
