import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useState, useEffect, useMemo, useCallback } from "react";

import { VersionSubmenuProps } from "./types";

import { AgenticPromptVersionResponse } from "@/lib/api-client/api-client";

const VersionSubmenu = ({
  open,
  promptName,
  taskId,
  apiClient,
  onVersionSelect,
  onClose,
  anchorEl,
}: VersionSubmenuProps) => {
  const [versions, setVersions] = useState<AgenticPromptVersionResponse[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchVersions = useCallback(async () => {
    if (!promptName || !taskId || !apiClient) {
      return;
    }

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
      setVersions([]);
    } finally {
      setLoading(false);
    }
  }, [apiClient, promptName, taskId]);

  // Sort versions in descending order (newest first)
  const sortedVersions = useMemo(() => {
    return [...versions].sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [versions]);

  const handleVersionClick = (version: number) => {
    onVersionSelect(version);
  };

  const handleClose = () => {
    onClose();
  };

  // Fetch versions when submenu opens
  useEffect(() => {
    if (open && promptName && taskId) {
      fetchVersions();
    }
  }, [open, promptName, taskId, fetchVersions]);

  return (
    <Menu
      open={open}
      onClose={handleClose}
      anchorEl={anchorEl}
      anchorOrigin={{
        vertical: "bottom",
        horizontal: "right",
      }}
      transformOrigin={{
        vertical: "top",
        horizontal: "left",
      }}
      slotProps={{
        paper: {
          style: {
            maxHeight: 300,
            width: 250,
          },
        },
      }}
    >
      {loading ? (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="100px"
        >
          <CircularProgress size={24} />
        </Box>
      ) : sortedVersions.length === 0 ? (
        <MenuItem disabled>
          <ListItemText
            primary={
              <Typography variant="body2" color="text.secondary">
                No versions found
              </Typography>
            }
          />
        </MenuItem>
      ) : (
        sortedVersions.map((version) => (
          <MenuItem
            key={version.version}
            onClick={() => handleVersionClick(version.version)}
          >
            <ListItemText
              primary={`Version ${version.version}`}
              secondary={new Date(version.created_at).toLocaleString()}
            />
          </MenuItem>
        ))
      )}
    </Menu>
  );
};

export default VersionSubmenu;
