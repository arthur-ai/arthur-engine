import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useState, useEffect, useMemo, useCallback } from "react";

import { VersionSelectionModalProps } from "./types";

import { AgenticPromptVersionResponse } from "@/lib/api-client/api-client";

const VersionSelectionModal = ({
  open,
  onClose,
  onSelectVersion,
  promptName,
  taskId,
  apiClient,
}: VersionSelectionModalProps) => {
  const [versions, setVersions] = useState<AgenticPromptVersionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchVersions = useCallback(async () => {
    setLoading(true);
    try {
      const response =
        await apiClient.api.getAllAgenticPromptVersionsApiV1TasksTaskIdPromptsPromptNameVersionsGet(
          {
            promptName,
            taskId,
            page_size: 100,
            sort: "desc",
          }
        );
      setVersions(response.data.versions);
    } catch (error) {
      console.error("Failed to fetch prompt versions:", error);
    } finally {
      setLoading(false);
    }
  }, [apiClient, promptName, taskId]);

  // Filter and sort versions
  const filteredVersions = useMemo(() => {
    if (!searchTerm) {
      return versions.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    }

    return versions
      .filter((version) => {
        const versionStr = version.version.toString();
        const dateStr = new Date(version.created_at).toLocaleString();
        const searchLower = searchTerm.toLowerCase();

        return (
          versionStr.toLowerCase().includes(searchLower) ||
          dateStr.toLowerCase().includes(searchLower)
        );
      })
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
  }, [versions, searchTerm]);

  const handleVersionClick = (version: number) => {
    onSelectVersion(version);
  };

  const handleClose = () => {
    setSearchTerm("");
    onClose();
  };

  // Fetch versions when modal opens
  useEffect(() => {
    if (open && apiClient && taskId && promptName) {
      fetchVersions();
    }
  }, [open, apiClient, taskId, promptName, fetchVersions]);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Select Version for "{promptName}"</DialogTitle>

      <DialogContent>
        <TextField
          fullWidth
          label="Search versions..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          margin="normal"
          variant="outlined"
        />

        {loading ? (
          <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            minHeight="200px"
          >
            <CircularProgress />
          </Box>
        ) : (
          <List>
            {filteredVersions.length === 0 ? (
              <ListItem>
                <ListItemText
                  primary={
                    <Typography variant="body2" color="text.secondary">
                      {searchTerm
                        ? "No versions match your search"
                        : "No versions found"}
                    </Typography>
                  }
                />
              </ListItem>
            ) : (
              filteredVersions.map((version) => (
                <ListItem key={version.version} disablePadding>
                  <ListItemButton
                    onClick={() => handleVersionClick(version.version)}
                  >
                    <ListItemText
                      primary={`Version ${version.version}`}
                      secondary={`Created: ${new Date(
                        version.created_at
                      ).toLocaleString()}`}
                    />
                  </ListItemButton>
                </ListItem>
              ))
            )}
          </List>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
};

export default VersionSelectionModal;
