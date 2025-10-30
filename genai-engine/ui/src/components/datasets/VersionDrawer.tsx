import CloseIcon from "@mui/icons-material/Close";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import React, { useCallback } from "react";

import { useDatasetVersionHistory } from "@/hooks/useDatasetVersionHistory";
import { DatasetVersionMetadataResponse } from "@/lib/api-client/api-client";

interface VersionDrawerProps {
  taskId: string;
  datasetId: string;
  datasetName: string;
  currentVersionNumber?: number;
  latestVersionNumber?: number;
  selectedVersionNumber: number | null;
  onVersionClick: (versionNumber: number) => void;
  onClose: () => void;
  onVersionSelect?: (versionNumber: number) => void;
}

export const VersionDrawer: React.FC<VersionDrawerProps> = ({
  datasetId,
  datasetName,
  currentVersionNumber,
  latestVersionNumber,
  selectedVersionNumber,
  onVersionClick,
  onClose,
  onVersionSelect,
}) => {
  const { versions, totalCount, isLoading, error } =
    useDatasetVersionHistory(datasetId);

  const handleVersionClick = useCallback(
    (version: DatasetVersionMetadataResponse) => {
      onVersionClick(version.version_number);
    },
    [onVersionClick]
  );

  const handleSwitchToVersion = useCallback(
    (versionNumber: number) => {
      if (onVersionSelect) {
        onVersionSelect(versionNumber);
      }
    },
    [onVersionSelect]
  );

  const formatDate = (timestamp: number): string => {
    const date = new Date(timestamp);
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
        {isLoading && (
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
              {error.message || "Failed to load versions"}
            </Typography>
          </Box>
        )}

        {!isLoading && !error && versions.length === 0 && (
          <Box sx={{ py: 4, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              No versions yet
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              Versions are created when you save changes
            </Typography>
          </Box>
        )}

        {!isLoading && !error && versions.length > 0 && (
          <Stack spacing={1.5}>
            {versions.map((version) => {
              const isSelected =
                selectedVersionNumber === version.version_number;
              const isViewing = currentVersionNumber === version.version_number;
              const isLatest = version.version_number === latestVersionNumber;

              return (
                <Box
                  key={version.version_number}
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
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                      flexWrap="wrap"
                      gap={0.5}
                    >
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontWeight: 600,
                          color: isSelected ? "primary.main" : "text.primary",
                        }}
                      >
                        Version {version.version_number}
                      </Typography>
                      <Box sx={{ display: "flex", gap: 0.5 }}>
                        {isLatest && (
                          <Chip
                            label="Latest"
                            size="small"
                            color="primary"
                            sx={{ height: 20, fontSize: "0.7rem" }}
                          />
                        )}
                        {isViewing && (
                          <Chip
                            label="Viewing"
                            size="small"
                            color="success"
                            sx={{ height: 20, fontSize: "0.7rem" }}
                          />
                        )}
                      </Box>
                    </Stack>

                    <Typography variant="caption" color="text.secondary">
                      {formatDate(version.created_at)}
                    </Typography>

                    {isSelected && !isViewing && (
                      <Button
                        variant="contained"
                        size="small"
                        fullWidth
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSwitchToVersion(version.version_number);
                        }}
                        sx={{ mt: 1 }}
                      >
                        View this version
                      </Button>
                    )}
                  </Stack>
                </Box>
              );
            })}
          </Stack>
        )}
      </Box>

      {!isLoading && !error && versions.length > 0 && (
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
            {totalCount} version{totalCount !== 1 ? "s" : ""} total
          </Typography>
        </Box>
      )}
    </Box>
  );
};
