import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Snackbar from "@mui/material/Snackbar";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

import { VersionTagsDialog } from "./VersionTagsDialog";

import { useDeleteRagVersion } from "@/hooks/rag-search-settings/useDeleteRagVersion";
import { useRagConfigVersions } from "@/hooks/rag-search-settings/useRagConfigVersions";
import useSnackbar from "@/hooks/useSnackbar";
import type { RagSearchSettingConfigurationResponse } from "@/lib/api-client/api-client";

interface ConfigVersionsDrawerProps {
  open: boolean;
  onClose: () => void;
  config: RagSearchSettingConfigurationResponse;
  currentVersion?: number | null;
  onVersionLoad: (version: number) => void;
}

export const ConfigVersionsDrawer: React.FC<ConfigVersionsDrawerProps> = ({ open, onClose, config, currentVersion, onVersionLoad }) => {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [tagsDialogOpen, setTagsDialogOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<{ versionNumber: number; tags: string[] } | null>(null);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const { data, isLoading } = useRagConfigVersions(config.id, {
    page,
    page_size: pageSize,
    sort: "desc",
  });

  const deleteVersion = useDeleteRagVersion();

  const versions = data?.versions ?? [];
  const count = data?.count ?? 0;

  const handleEditTags = (versionNumber: number, currentTags: string[]) => {
    setSelectedVersion({ versionNumber, tags: currentTags });
    setTagsDialogOpen(true);
  };

  const handleDeleteVersion = async (versionNumber: number) => {
    if (window.confirm(`Are you sure you want to soft delete version ${versionNumber}?`)) {
      try {
        await deleteVersion.mutateAsync({ configId: config.id, versionNumber });
        showSnackbar(`Version ${versionNumber} deleted successfully`, "success");
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : "Unknown error";
        showSnackbar(`Failed to delete version: ${errorMessage}`, "error");
      }
    }
  };

  const handleVersionLoad = (versionNumber: number) => {
    onVersionLoad(versionNumber);
    onClose();
  };

  return (
    <>
      <Drawer anchor="right" open={open} onClose={onClose} sx={{ "& .MuiDrawer-paper": { width: 600 } }}>
        <Box sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            {config.name}
          </Typography>
          {config.description && (
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {config.description}
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Latest Version: {config.latest_version_number}
          </Typography>

          {isLoading ? (
            <div className="p-8 text-center">Loading versions...</div>
          ) : versions.length === 0 ? (
            <div className="p-8 text-center text-gray-500">No versions available.</div>
          ) : (
            <>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Version</TableCell>
                    <TableCell>Tags</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {versions.map((version) => (
                    <TableRow
                      key={version.version_number}
                      sx={{
                        backgroundColor: version.version_number === currentVersion ? "action.selected" : "inherit",
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2">v{version.version_number}</Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
                          {version.tags?.map((tag) => (
                            <Chip key={tag} label={tag} size="small" variant="outlined" />
                          ))}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{new Date(version.created_at).toLocaleDateString()}</Typography>
                      </TableCell>
                      <TableCell>
                        <IconButton size="small" onClick={() => handleVersionLoad(version.version_number)} title="Load version">
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleEditTags(version.version_number, version.tags || [])} title="Edit tags">
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" onClick={() => handleDeleteVersion(version.version_number)} title="Delete version">
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <TablePagination
                component="div"
                count={count}
                page={page}
                onPageChange={(_e, newPage) => setPage(newPage)}
                rowsPerPage={pageSize}
                onRowsPerPageChange={(e) => {
                  setPageSize(parseInt(e.target.value));
                  setPage(0);
                }}
                rowsPerPageOptions={[10, 20, 50]}
              />
            </>
          )}

          <Box sx={{ mt: 2, display: "flex", justifyContent: "flex-end" }}>
            <Button variant="outlined" onClick={onClose}>
              Close
            </Button>
          </Box>
        </Box>
      </Drawer>

      {selectedVersion && (
        <VersionTagsDialog
          open={tagsDialogOpen}
          onClose={() => {
            setTagsDialogOpen(false);
            setSelectedVersion(null);
          }}
          configId={config.id}
          versionNumber={selectedVersion.versionNumber}
          currentTags={selectedVersion.tags}
          allPossibleTags={config.all_possible_tags || []}
        />
      )}

      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </>
  );
};
