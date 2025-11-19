import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  IconButton,
  Tooltip,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";

import { DatasetTransform } from "./types";

interface TransformDetailsModalProps {
  open: boolean;
  onClose: () => void;
  transform: DatasetTransform | null;
}

export const TransformDetailsModal: React.FC<TransformDetailsModalProps> = ({
  open,
  onClose,
  transform,
}) => {
  const [copied, setCopied] = useState(false);

  if (!transform) return null;

  const handleCopyId = async () => {
    try {
      await navigator.clipboard.writeText(transform.id);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy transform ID:", err);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Transform Details: {transform.name}</DialogTitle>
      <DialogContent>
        <Box sx={{ mt: 1 }}>
          {/* Transform ID Section */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
              Transform ID
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                p: 1.5,
                backgroundColor: "grey.50",
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  fontFamily: "monospace",
                  fontSize: 13,
                  flex: 1,
                  wordBreak: "break-all",
                }}
              >
                {transform.id}
              </Typography>
              <Tooltip title={copied ? "Copied!" : "Copy ID"}>
                <IconButton
                  size="small"
                  onClick={handleCopyId}
                  sx={{
                    color: copied ? "success.main" : "text.secondary",
                  }}
                >
                  {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {transform.description && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
                Description
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {transform.description}
              </Typography>
            </Box>
          )}

          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
              Column Mappings ({transform.definition.columns.length})
            </Typography>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 1 }}>
              {transform.definition.columns.map((col, idx) => (
                <Box
                  key={idx}
                  sx={{
                    p: 2,
                    backgroundColor: "grey.50",
                    borderRadius: 1,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="body2" fontWeight="medium">
                    {col.column_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Span: <code>{col.span_name}</code> → Path: <code>{col.attribute_path}</code>
                  </Typography>
                  {col.fallback !== undefined && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      Fallback: {JSON.stringify(col.fallback)}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          </Box>

          <Box>
            <Typography variant="subtitle2" fontWeight="medium" gutterBottom>
              Full JSON Definition
            </Typography>
            <pre
              style={{
                backgroundColor: "#ffffff",
                padding: 16,
                borderRadius: 4,
                overflow: "auto",
                maxHeight: 400,
                fontSize: 12,
                border: "1px solid #e0e0e0",
              }}
            >
              {JSON.stringify(transform.definition, null, 2)}
            </pre>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TransformDetailsModal;
