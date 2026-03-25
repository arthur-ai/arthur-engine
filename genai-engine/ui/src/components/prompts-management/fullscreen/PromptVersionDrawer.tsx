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
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TablePagination from "@mui/material/TablePagination";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";

import { usePromptVersions } from "../hooks/usePromptVersions";
import type { PromptVersionDrawerProps } from "../types";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { usePagination } from "@/hooks/usePagination";
import { formatDateInTimezone } from "@/utils/formatters";

const PromptVersionDrawer = ({
  open,
  onClose,
  taskId,
  promptName,
  selectedVersion,
  latestVersion,
  onSelectVersion,
  onDelete,
}: PromptVersionDrawerProps) => {
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [excludeDeleted, setExcludeDeleted] = useState(true);
  const { page, rowsPerPage, handlePageChange, handleRowsPerPageChange, resetPage } = usePagination(10);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [versionToDelete, setVersionToDelete] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const { timezone, use24Hour } = useDisplaySettings();
  const { versions, count, isLoading, error, refetch } = usePromptVersions(taskId, promptName, {
    sort: sortOrder,
    exclude_deleted: excludeDeleted,
    page,
    pageSize: rowsPerPage,
  });

  const handleVersionClick = useCallback(
    (version: number) => {
      onSelectVersion(version);
    },
    [onSelectVersion]
  );

  const handleDeleteClick = useCallback((e: React.MouseEvent, version: number) => {
    e.stopPropagation();
    setVersionToDelete(version);
    setDeleteDialogOpen(true);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (versionToDelete === null || !onDelete) return;

    try {
      setIsDeleting(true);
      await onDelete(versionToDelete);
      setDeleteDialogOpen(false);
      setVersionToDelete(null);
      refetch();
    } catch (err) {
      console.error("Failed to delete prompt version:", err);
    } finally {
      setIsDeleting(false);
    }
  }, [versionToDelete, onDelete, refetch]);

  const handleDeleteCancel = useCallback(() => {
    setDeleteDialogOpen(false);
    setVersionToDelete(null);
  }, []);

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      open={open}
      onClose={onClose}
      sx={{
        width: 400,
        flexShrink: 0,
        position: "relative",
        "& .MuiDrawer-paper": {
          width: 400,
          boxSizing: "border-box",
          position: "relative",
          height: "100%",
          borderRight: "1px solid",
          borderColor: "divider",
          overflow: "visible",
        },
      }}
    >
      <Box sx={{ p: 2, display: "flex", flexDirection: "column", height: "100%" }}>
        <Typography variant="h6" noWrap sx={{ mb: 2, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis" }}>
          Versions: {promptName}
        </Typography>

        <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
          <Chip
            label={`Sort: ${sortOrder === "asc" ? "Oldest First" : "Newest First"}`}
            onClick={() => {
              setSortOrder(sortOrder === "asc" ? "desc" : "asc");

              resetPage();
            }}
            clickable
            size="small"
          />
          <Chip
            label={excludeDeleted ? "Hide Deleted" : "Show Deleted"}
            onClick={() => {
              setExcludeDeleted((prev) => !prev);
              resetPage();
            }}
            clickable
            size="small"
            color={excludeDeleted ? "default" : "warning"}
            variant={excludeDeleted ? "filled" : "outlined"}
          />
        </Box>

        <Divider sx={{ mb: 2 }} />

        {isLoading && (
          <Box sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              Loading versions...
            </Typography>
          </Box>
        )}

        {error && (
          <Box sx={{ p: 2 }}>
            <Typography variant="body2" color="error">
              Error loading versions: {error.message}
            </Typography>
          </Box>
        )}

        {!isLoading && !error && versions.length === 0 && (
          <Box sx={{ p: 2, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No versions found
            </Typography>
          </Box>
        )}

        {!isLoading && !error && versions.length > 0 && (
          <List sx={{ flex: 1, overflow: "auto" }}>
            {versions.map((version) => {
              const isSelected = selectedVersion === version.version;
              const isDeleted = !!version.deleted_at;
              const isLatest = version.version === latestVersion && !isDeleted;

              // Prioritize tags: production, then others
              const tags = version.tags || [];
              const hasProduction = tags.some((tag) => tag.toLowerCase() === "production");
              const otherTags = tags.filter((tag) => tag.toLowerCase() !== "production");

              // Build display tags: Production tag first, then Latest badge, then other tags up to max 3 total
              // Don't show any tags for deleted versions
              const displayTags: Array<{ label: string; type: "latest" | "production" | "other" }> = [];

              if (!isDeleted) {
                if (hasProduction) displayTags.push({ label: "production", type: "production" });
                if (isLatest) displayTags.push({ label: "Latest", type: "latest" });

                // Add other tags up to max of 3 total
                const remainingSlots = 3 - displayTags.length;
                otherTags.slice(0, remainingSlots).forEach((tag) => {
                  displayTags.push({ label: tag, type: "other" });
                });
              }

              return (
                <ListItem key={version.version} disablePadding>
                  <ListItemButton
                    selected={isSelected}
                    onClick={() => !isDeleted && handleVersionClick(version.version)}
                    disabled={isDeleted}
                    sx={{
                      backgroundColor: isSelected ? "action.selected" : "transparent",
                      "&:hover": {
                        backgroundColor: isDeleted ? "transparent" : "action.hover",
                      },
                      "&.Mui-disabled": {
                        opacity: 1,
                      },
                      cursor: isDeleted ? "not-allowed" : "pointer",
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, flexWrap: "wrap" }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 500,
                              color: isDeleted ? "text.disabled" : "text.primary",
                              textDecoration: isDeleted ? "line-through" : "none",
                            }}
                          >
                            Version {version.version}
                          </Typography>
                          {displayTags.map((tag, idx) => {
                            let color: "default" | "primary" | "success" = "default";
                            let variant: "filled" | "outlined" = "filled";

                            if (tag.type === "latest") {
                              color = "default";
                            } else if (tag.type === "production") {
                              color = "success";
                            } else if (tag.type === "other") {
                              color = "primary";
                              variant = "outlined";
                            }

                            return (
                              <Chip
                                key={`${tag.label}-${idx}`}
                                label={tag.label}
                                size="small"
                                color={color}
                                variant={variant}
                                sx={{ height: 18, fontSize: "0.7rem" }}
                              />
                            );
                          })}
                        </Box>
                      }
                      secondary={
                        <Box component="span" sx={{ mt: 0.5, display: "block" }}>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            component="span"
                            sx={{ color: isDeleted ? "text.disabled" : "text.secondary" }}
                          >
                            {version.model_provider} / {version.model_name}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            component="span"
                            sx={{
                              display: "block",
                              mt: 0.5,
                              color: isDeleted ? "text.disabled" : "text.secondary",
                            }}
                          >
                            {formatDateInTimezone(version.created_at, timezone, { hour12: !use24Hour })}
                          </Typography>
                          {isDeleted && version.deleted_at && (
                            <Typography
                              variant="caption"
                              component="span"
                              sx={{
                                display: "block",
                                mt: 0.5,
                                color: "text.disabled",
                              }}
                            >
                              Deleted at: {formatDateInTimezone(version.deleted_at, timezone, { hour12: !use24Hour })}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    {!isDeleted && (
                      <IconButton
                        size="small"
                        onClick={(e) => handleDeleteClick(e, version.version)}
                        sx={{ color: "error.main" }}
                        aria-label="Delete version"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )}
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>
        )}

        {!isLoading && !error && count > 0 && (
          <TablePagination
            component="div"
            count={count}
            page={page}
            onPageChange={handlePageChange}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleRowsPerPageChange}
            rowsPerPageOptions={[10, 25, 50]}
            sx={{ borderTop: 1, borderColor: "divider", flexShrink: 0 }}
          />
        )}
      </Box>

      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-version-dialog-title"
        aria-describedby="delete-version-dialog-description"
      >
        <DialogTitle id="delete-version-dialog-title">Delete Version?</DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-version-dialog-description">
            Are you sure you want to delete <strong>Version {versionToDelete}</strong> of <strong>{promptName}</strong>?
          </DialogContentText>
          <Box sx={{ mt: 2, p: 2, bgcolor: "warning.lighter", borderRadius: 1 }}>
            <strong>Warning:</strong> This version and all of its contents will be deleted. This action cannot be undone.
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
    </Drawer>
  );
};

export default PromptVersionDrawer;
