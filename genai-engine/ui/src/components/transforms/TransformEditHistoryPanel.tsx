import HistoryIcon from "@mui/icons-material/History";
import { Alert, Box, CircularProgress, Divider, Stack, Typography } from "@mui/material";
import React from "react";

import { useTransformVersions } from "./hooks/useTransformVersions";

interface TransformEditHistoryPanelProps {
  transformId: string;
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

function buildChangeSummary(configSnapshot: { variables?: unknown[] }): string {
  const variables = configSnapshot?.variables;
  if (Array.isArray(variables)) {
    const count = variables.length;
    return `${count} variable${count !== 1 ? "s" : ""} defined`;
  }
  return "Configuration updated";
}

export const TransformEditHistoryPanel: React.FC<TransformEditHistoryPanelProps> = ({ transformId }) => {
  const { data: versions, isLoading, isError } = useTransformVersions(transformId);

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
                {buildChangeSummary(version.definition)}
              </Typography>
            </Box>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
};

export default TransformEditHistoryPanel;
