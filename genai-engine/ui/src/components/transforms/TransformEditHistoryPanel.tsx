import HistoryIcon from "@mui/icons-material/History";
import PersonIcon from "@mui/icons-material/Person";
import RestoreIcon from "@mui/icons-material/Restore";
import { Alert, Box, Button, CircularProgress, Divider, Stack, Typography } from "@mui/material";
import React, { useState } from "react";

import { useRestoreTransformVersionMutation } from "./hooks/useRestoreTransformVersionMutation";
import { useTransformVersions } from "./hooks/useTransformVersions";
import RestoreTransformVersionDialog from "./RestoreTransformVersionDialog";

interface TransformEditHistoryPanelProps {
  transformId: string;
  onRestoreSuccess?: () => void;
}

function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildChangeSummary(configSnapshot: Record<string, unknown>): string {
  const variables = configSnapshot?.variables;
  if (Array.isArray(variables)) {
    const count = variables.length;
    return `${count} variable${count !== 1 ? "s" : ""} defined`;
  }
  return "Configuration updated";
}

export const TransformEditHistoryPanel: React.FC<TransformEditHistoryPanelProps> = ({ transformId, onRestoreSuccess }) => {
  const { data: versions, isLoading, isError } = useTransformVersions(transformId);
  const [pendingVersionId, setPendingVersionId] = useState<string | null>(null);
  const [pendingVersionNumber, setPendingVersionNumber] = useState<number | null>(null);

  const restoreMutation = useRestoreTransformVersionMutation(transformId, onRestoreSuccess);

  const handleRestoreClick = (versionId: string, versionNumber: number) => {
    setPendingVersionId(versionId);
    setPendingVersionNumber(versionNumber);
  };

  const handleDialogClose = () => {
    if (!restoreMutation.isPending) {
      setPendingVersionId(null);
      setPendingVersionNumber(null);
    }
  };

  const handleRestoreConfirm = () => {
    if (!pendingVersionId) return;
    restoreMutation.mutate(pendingVersionId, {
      onSuccess: () => {
        setPendingVersionId(null);
        setPendingVersionNumber(null);
      },
    });
  };

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (isError) {
    return <Alert severity="error">Failed to load version history.</Alert>;
  }

  if (!versions || versions.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No version history available.
      </Typography>
    );
  }

  return (
    <>
      <Stack divider={<Divider />} spacing={0}>
        {versions.map((version, index) => (
          <Box
            key={version.id}
            sx={{
              py: 1.5,
              px: 0,
              "&:first-of-type": { pt: 0 },
            }}
          >
            <Stack direction="row" spacing={1.5} alignItems="flex-start">
              <Box
                sx={{
                  mt: 0.25,
                  width: 28,
                  height: 28,
                  borderRadius: "50%",
                  backgroundColor: "primary.50",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <HistoryIcon sx={{ fontSize: 16, color: "primary.main" }} />
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.25 }}>
                  <Typography variant="body2" fontWeight="medium">
                    Version {version.version_number}
                  </Typography>
                  {index === 0 && (
                    <Typography variant="caption" color="primary.main" fontWeight="medium">
                      (current)
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {formatTimestamp(version.created_at)}
                  </Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                  {buildChangeSummary(version.config_snapshot)}
                </Typography>
                {version.author && (
                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <PersonIcon sx={{ fontSize: 13, color: "text.disabled" }} />
                    <Typography variant="caption" color="text.disabled">
                      {version.author}
                    </Typography>
                  </Stack>
                )}
              </Box>
              {index !== 0 && (
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<RestoreIcon sx={{ fontSize: 14 }} />}
                  onClick={() => handleRestoreClick(version.id, version.version_number)}
                  sx={{ flexShrink: 0, alignSelf: "center" }}
                >
                  Restore
                </Button>
              )}
            </Stack>
          </Box>
        ))}
      </Stack>

      <RestoreTransformVersionDialog
        open={!!pendingVersionId}
        versionNumber={pendingVersionNumber}
        onClose={handleDialogClose}
        onConfirm={handleRestoreConfirm}
        isRestoring={restoreMutation.isPending}
      />
    </>
  );
};

export default TransformEditHistoryPanel;
