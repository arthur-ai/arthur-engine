import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import TagIcon from "@mui/icons-material/Tag";
import { Alert, Box, Button, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Divider, Typography } from "@mui/material";

import { useTransformVersion } from "./hooks/useTransformVersion";

interface TransformVersionSnapshotModalProps {
  open: boolean;
  onClose: () => void;
  transformId: string | null;
  versionId: string | null;
}

interface VariableDefinition {
  variable_name: string;
  span_name: string;
  attribute_path: string;
  fallback?: unknown;
}

interface ConfigSnapshot {
  variables?: VariableDefinition[];
}

export const TransformVersionSnapshotModal: React.FC<TransformVersionSnapshotModalProps> = ({ open, onClose, transformId, versionId }) => {
  const { data: version, isLoading, error } = useTransformVersion(transformId, versionId);

  const snapshot = version?.definition as ConfigSnapshot | undefined;

  const formattedDate = version?.created_at
    ? new Date(version.created_at).toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography variant="h6" component="span">
            Transform Version Snapshot
          </Typography>
          {version && (
            <Chip icon={<TagIcon sx={{ fontSize: 14 }} />} label={`v${version.version_number}`} size="small" color="primary" variant="outlined" />
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 1 }}>
            Failed to load version snapshot.
          </Alert>
        )}

        {version && snapshot && (
          <Box sx={{ mt: 1 }}>
            {/* Metadata row */}
            <Box sx={{ display: "flex", gap: 3, mb: 3, flexWrap: "wrap" }}>
              {formattedDate && (
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <CalendarTodayIcon sx={{ fontSize: 16, color: "text.secondary" }} />
                  <Typography variant="body2" color="text.secondary">
                    {formattedDate}
                  </Typography>
                </Box>
              )}
            </Box>

            <Divider sx={{ mb: 3 }} />

            {/* Variable Mappings */}
            {snapshot.variables && snapshot.variables.length > 0 && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
                  Variable Mappings ({snapshot.variables.length})
                </Typography>
                <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 1 }}>
                  {snapshot.variables.map((variable, idx) => (
                    <Box
                      key={idx}
                      sx={{
                        p: 2,
                        backgroundColor: "action.hover",
                        borderRadius: 1,
                        border: "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="body2" fontWeight="medium">
                        {variable.variable_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Span: <code>{variable.span_name}</code> → Path: <code>{variable.attribute_path}</code>
                      </Typography>
                      {variable.fallback !== undefined && variable.fallback !== null && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          Fallback: {JSON.stringify(variable.fallback)}
                        </Typography>
                      )}
                    </Box>
                  ))}
                </Box>
              </Box>
            )}

            {/* Full JSON */}
            <Box>
              <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
                Full JSON Snapshot
              </Typography>
              <Box
                component="pre"
                sx={{
                  backgroundColor: "background.paper",
                  p: 2,
                  borderRadius: 1,
                  overflow: "auto",
                  maxHeight: 300,
                  fontSize: 12,
                  border: 1,
                  borderColor: "divider",
                  m: 0,
                }}
              >
                {JSON.stringify(snapshot, null, 2)}
              </Box>
            </Box>
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TransformVersionSnapshotModal;
