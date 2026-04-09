import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import EditIcon from "@mui/icons-material/Edit";
import RestoreIcon from "@mui/icons-material/Restore";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useState, useCallback } from "react";

import { useDisplaySettings } from "@/contexts/DisplaySettingsContext";
import { TraceTransformResponse, TraceTransformVersionResponse } from "@/lib/api-client/api-client";
import { formatDateInTimezone } from "@/utils/formatters";

interface VariableDefinition {
  variable_name: string;
  span_name: string;
  attribute_path: string;
  fallback?: unknown;
}

interface TransformDetailViewProps {
  transform: TraceTransformResponse | null;
  versionData: TraceTransformVersionResponse | null;
  isVersionLoading: boolean;
  versionError: Error | null;
  isLatest: boolean;
  onClose: () => void;
  onEdit: () => void;
  onRestore: (versionId: string, versionNumber: number) => void;
}

const TransformDetailView = ({
  transform,
  versionData,
  isVersionLoading,
  versionError,
  isLatest,
  onClose,
  onEdit,
  onRestore,
}: TransformDetailViewProps) => {
  const [copied, setCopied] = useState(false);
  const { timezone, use24Hour } = useDisplaySettings();

  const handleCopyId = useCallback(async () => {
    if (!transform?.id) return;
    try {
      await navigator.clipboard.writeText(transform.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy transform ID:", err);
    }
  }, [transform?.id]);

  if (isVersionLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100%" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (versionError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Error loading version: {versionError.message}</Alert>
      </Box>
    );
  }

  if (!transform) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No transform data available</Alert>
      </Box>
    );
  }

  // Use the version snapshot if viewing a historical version, otherwise use current transform definition
  const definition = versionData
    ? (versionData.config_snapshot as { variables?: VariableDefinition[] })
    : (transform.definition as { variables?: VariableDefinition[] });
  const variables = definition?.variables ?? [];
  const versionNumber = versionData?.version_number ?? null;
  const createdAt = versionData?.created_at ?? transform.created_at;
  const author = versionData?.author ?? null;

  return (
    <Box sx={{ p: 3, height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3, flexShrink: 0 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap", minWidth: 0, overflow: "hidden" }}>
          <Typography variant="h5" noWrap sx={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", maxWidth: "100%" }}>
            {transform.name}
          </Typography>
          {versionNumber !== null && <Chip label={`Version ${versionNumber}`} size="small" sx={{ height: 24 }} />}
          {isLatest && <Chip label="Latest" size="small" color="default" sx={{ height: 24 }} />}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
          {isLatest && (
            <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={onEdit}>
              Edit
            </Button>
          )}
          {!isLatest && versionData && (
            <Button variant="outlined" size="small" startIcon={<RestoreIcon />} onClick={() => onRestore(versionData.id, versionData.version_number)}>
              Restore
            </Button>
          )}
          <IconButton onClick={onClose} aria-label="Close">
            <CloseIcon />
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 3, flex: 1, minHeight: 0, overflow: "auto" }}>
        {/* Metadata */}
        <Paper sx={{ p: 3, flexShrink: 0 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Metadata
          </Typography>
          <Box sx={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "flex-start" }}>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Transform ID
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.25 }}>
                <Typography variant="body2" sx={{ fontFamily: "monospace", fontSize: 12 }}>
                  {transform.id}
                </Typography>
                <Tooltip title={copied ? "Copied!" : "Copy ID"}>
                  <IconButton size="small" onClick={handleCopyId} sx={{ color: copied ? "success.main" : "text.secondary", p: 0.25 }}>
                    {copied ? <CheckIcon sx={{ fontSize: 14 }} /> : <ContentCopyIcon sx={{ fontSize: 14 }} />}
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">
                Created At
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>
                {formatDateInTimezone(createdAt, timezone, { hour12: !use24Hour })}
              </Typography>
            </Box>
            {author && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Author
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {author}
                </Typography>
              </Box>
            )}
            {transform.description && (
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Description
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {transform.description}
                </Typography>
              </Box>
            )}
          </Box>
        </Paper>

        {/* Variable Mappings */}
        <Paper sx={{ p: 3, flexShrink: 0 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Variable Mappings ({variables.length})
          </Typography>
          {variables.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No variable mappings defined.
            </Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {variables.map((variable, idx) => (
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
          )}
        </Paper>

        {/* Full JSON */}
        <Paper sx={{ p: 3, flexShrink: 0 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Full JSON Definition
          </Typography>
          <Box
            component="pre"
            sx={{
              backgroundColor: "background.paper",
              p: 2,
              borderRadius: 1,
              overflow: "auto",
              fontSize: 12,
              border: 1,
              borderColor: "divider",
              m: 0,
            }}
          >
            {JSON.stringify(definition, null, 2)}
          </Box>
        </Paper>
      </Box>
    </Box>
  );
};

export default TransformDetailView;
