import HistoryIcon from "@mui/icons-material/History";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";

import { TraceTransformVersionResponse, useTransformVersions } from "./hooks/useTransformVersions";

interface TransformEditHistoryProps {
  transformId: string;
}

function formatTimestamp(isoString: string): string {
  return new Date(isoString).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function summarizeChange(version: { definition: object; version_number: number }): string {
  const snapshot = version.definition as Record<string, unknown>;
  const variables = snapshot.variables;
  if (Array.isArray(variables)) {
    return `${variables.length} variable${variables.length !== 1 ? "s" : ""}`;
  }
  return "Config updated";
}

export const TransformEditHistory: React.FC<TransformEditHistoryProps> = ({ transformId }) => {
  const { data: versions = [], isLoading, error } = useTransformVersions(transformId);

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 1 }}>
        Failed to load edit history
      </Alert>
    );
  }

  if (versions.length === 0) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, py: 2, color: "text.secondary" }}>
        <HistoryIcon fontSize="small" />
        <Typography variant="body2">No edit history yet</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {versions.map((version: TraceTransformVersionResponse, idx: number) => (
        <Box key={version.id}>
          <Box
            sx={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              py: 1.5,
              px: 0,
            }}
          >
            <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1.5, flex: 1, minWidth: 0 }}>
              <Box
                sx={{
                  mt: 0.25,
                  minWidth: 28,
                  height: 20,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: "primary.50",
                  borderRadius: 0.75,
                  px: 0.75,
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 600, color: "primary.main", lineHeight: 1 }}>
                  v{version.version_number}
                </Typography>
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, color: "text.primary" }}>
                  {summarizeChange(version)}
                </Typography>
              </Box>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: "nowrap", ml: 2, flexShrink: 0 }}>
              {formatTimestamp(version.created_at)}
            </Typography>
          </Box>
          {idx < versions.length - 1 && <Divider />}
        </Box>
      ))}
    </Box>
  );
};

export default TransformEditHistory;
