import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import React from "react";

import { CopyableChip } from "@/components/common";
import { Highlight } from "@/components/common/Highlight";
import { useCopy } from "@/hooks/useCopy";

interface TraceContentModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  value: unknown;
  traceId?: string | null;
  spanId?: string | null;
}

const getFormattedContent = (value: unknown) => {
  if (value === null || value === undefined) {
    return { content: "", language: "text" };
  }

  const rawValue = typeof value === "string" ? value : (JSON.stringify(value, null, 2) ?? String(value));

  if (!rawValue) {
    return { content: "", language: "text" };
  }

  try {
    const parsed = JSON.parse(rawValue);
    return { content: JSON.stringify(parsed, null, 2), language: "json" };
  } catch {
    return { content: rawValue, language: "text" };
  }
};

export const TraceContentModal: React.FC<TraceContentModalProps> = ({ open, onClose, title, value, traceId, spanId }) => {
  const { enqueueSnackbar } = useSnackbar();
  const { handleCopy } = useCopy({
    onCopy: () => enqueueSnackbar("Copied to clipboard!", { variant: "success" }),
    onError: () => enqueueSnackbar("Failed to copy to clipboard", { variant: "error" }),
  });
  const { content, language } = getFormattedContent(value);
  const charCount = content.length;

  const handleCopyClick = () => {
    handleCopy(content);
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth onClick={(e) => e.stopPropagation()}>
        <DialogTitle>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 2 }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" gutterBottom>
                {title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {charCount.toLocaleString()} characters
              </Typography>
              {(traceId || spanId) && (
                <Box sx={{ display: "flex", gap: 1, mt: 1, flexWrap: "wrap" }}>
                  {traceId && (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Trace ID
                      </Typography>
                      <CopyableChip label={traceId} size="small" sx={{ fontFamily: "monospace" }} />
                    </Box>
                  )}
                  {spanId && (
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                      <Typography variant="caption" color="text.secondary">
                        Span ID
                      </Typography>
                      <CopyableChip label={spanId} size="small" sx={{ fontFamily: "monospace" }} />
                    </Box>
                  )}
                </Box>
              )}
            </Box>
            <IconButton size="small" onClick={handleCopyClick} title="Copy to clipboard" sx={{ "&:hover": { color: "primary.main" } }}>
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          <Box sx={{ minHeight: "200px", maxHeight: "60vh", overflow: "auto" }}>
            {content ? (
              <Highlight code={content} language={language} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No content available.
              </Typography>
            )}
          </Box>
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleCopyClick} variant="outlined" size="small" disabled={!content}>
            Copy
          </Button>
          <Button onClick={onClose} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
