import {
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import React, { useCallback, useEffect, useState } from "react";

import { fetchDatasetVersions } from "@/services/mockDatasetService";
import { DatasetVersion } from "@/types/dataset";

interface VersionDrawerProps {
  taskId: string;
  datasetId: string;
  datasetName: string;
  onClose: () => void;
  onVersionSelect?: (version: DatasetVersion) => void;
}

export const VersionDrawer: React.FC<VersionDrawerProps> = ({
  taskId,
  datasetId,
  datasetName,
  onClose,
  onVersionSelect,
}) => {
  const [versions, setVersions] = useState<DatasetVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(
    null
  );

  // Fetch versions on mount
  useEffect(() => {
    const loadVersions = async () => {
      try {
        setLoading(true);
        setError(null);
        const fetchedVersions = await fetchDatasetVersions(taskId, datasetId);
        setVersions(fetchedVersions);

        // Auto-select current version
        const currentVersion = fetchedVersions.find((v) => v.isCurrent);
        if (currentVersion) {
          setSelectedVersionId(currentVersion.id);
        }
      } catch (err) {
        console.error("Failed to fetch versions:", err);
        setError(
          err instanceof Error ? err.message : "Failed to load versions"
        );
      } finally {
        setLoading(false);
      }
    };

    loadVersions();
  }, [taskId, datasetId]);

  const handleVersionClick = useCallback(
    (version: DatasetVersion) => {
      setSelectedVersionId(version.id);
      if (onVersionSelect) {
        onVersionSelect(version);
      }
    },
    [onVersionSelect]
  );

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  return (
    <Box
      sx={{
        flex: "0 0 400px",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
        borderLeft: 1,
        borderColor: "divider",
        overflow: "hidden",
      }}
    >
      {/* Header - Fixed */}
      <Box
        sx={{
          p: 2,
          borderBottom: 1,
          borderColor: "divider",
          flexShrink: 0,
        }}
      >
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <Box>
            <Typography
              variant="h6"
              sx={{ fontWeight: 600, mb: 0.5, color: "text.primary" }}
            >
              Version History
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {datasetName}
            </Typography>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Stack>
      </Box>

      {/* Content - Scrollable */}
      <Box sx={{ flex: 1, overflow: "auto", p: 2 }}>
        {loading && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              py: 4,
            }}
          >
            <CircularProgress size={32} />
          </Box>
        )}

        {error && (
          <Box sx={{ py: 2 }}>
            <Typography variant="body2" color="error">
              {error}
            </Typography>
          </Box>
        )}

        {!loading && !error && versions.length === 0 && (
          <Box sx={{ py: 4, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No versions found
            </Typography>
          </Box>
        )}

        {!loading && !error && versions.length > 0 && (
          <Stack spacing={1.5}>
            {versions.map((version) => {
              const isSelected = selectedVersionId === version.id;

              return (
                <Box
                  key={version.id}
                  onClick={() => handleVersionClick(version)}
                  sx={{
                    p: 2,
                    border: 1,
                    borderColor: isSelected ? "primary.main" : "divider",
                    borderRadius: 1,
                    backgroundColor: isSelected
                      ? "action.selected"
                      : "background.paper",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                    "&:hover": {
                      borderColor: "primary.main",
                      backgroundColor: "action.hover",
                    },
                  }}
                >
                  <Stack spacing={1.5}>
                    {/* Version number and current badge */}
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontWeight: 600,
                          color: isSelected ? "primary.main" : "text.primary",
                        }}
                      >
                        Version {version.versionNumber}
                      </Typography>
                      {version.isCurrent && (
                        <Chip
                          label="Current"
                          size="small"
                          color="primary"
                          sx={{ height: 20, fontSize: "0.7rem" }}
                        />
                      )}
                    </Stack>

                    {/* Last updated time */}
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(version.createdAt)}
                    </Typography>

                    {/* Confirm button - show only for selected version */}
                    {isSelected && !version.isCurrent && (
                      <Button
                        variant="contained"
                        size="small"
                        fullWidth
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onVersionSelect) {
                            onVersionSelect(version);
                          }
                          // TODO: Implement actual version switch logic
                          console.log(
                            "Switching to version:",
                            version.versionNumber
                          );
                        }}
                        sx={{ mt: 1 }}
                      >
                        Switch to this version
                      </Button>
                    )}
                  </Stack>
                </Box>
              );
            })}
          </Stack>
        )}
      </Box>

      {/* Footer info */}
      {!loading && !error && versions.length > 0 && (
        <Box
          sx={{
            p: 2,
            borderTop: 1,
            borderColor: "divider",
            backgroundColor: "grey.50",
            flexShrink: 0,
          }}
        >
          <Typography variant="caption" color="text.secondary">
            {versions.length} version{versions.length !== 1 ? "s" : ""} total
          </Typography>
        </Box>
      )}
    </Box>
  );
};
