import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import {
  Box,
  IconButton,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tooltip,
} from "@mui/material";
import React, { useState } from "react";

interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

interface MessageDisplayProps {
  message: Message;
}

export const MessageDisplay: React.FC<MessageDisplayProps> = ({ message }) => {
  const getRoleStyles = (role: Message["role"]) => {
    switch (role) {
      case "system":
        return {
          bg: "bg-gray-100",
          border: "border-gray-300",
          label: "System",
          labelColor: "text-gray-700",
        };
      case "user":
        return {
          bg: "bg-blue-50",
          border: "border-blue-200",
          label: "User",
          labelColor: "text-blue-700",
        };
      case "assistant":
        return {
          bg: "bg-green-50",
          border: "border-green-200",
          label: "Assistant",
          labelColor: "text-green-700",
        };
      default:
        return {
          bg: "bg-gray-50",
          border: "border-gray-200",
          label: role,
          labelColor: "text-gray-700",
        };
    }
  };

  const styles = getRoleStyles(message.role);

  return (
    <Box className={`p-3 ${styles.bg} border ${styles.border} rounded mb-2`}>
      <Typography variant="caption" className={`font-semibold ${styles.labelColor} block mb-1`}>
        {styles.label}
      </Typography>
      <Typography variant="body2" className="whitespace-pre-wrap text-gray-900">
        {message.content}
      </Typography>
    </Box>
  );
};

interface VariableTileProps {
  variableName: string;
  value: string;
}

const MAX_TILE_LENGTH = 200;

export const VariableTile: React.FC<VariableTileProps> = ({ variableName, value }) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const isTruncated = value.length > MAX_TILE_LENGTH;
  const displayValue = isTruncated ? value.substring(0, MAX_TILE_LENGTH) + "..." : value;

  const handleCopy = () => {
    navigator.clipboard.writeText(value);
  };

  return (
    <>
      <Box
        className="p-3 bg-gray-50 border border-gray-200 rounded relative"
        onClick={isTruncated ? () => setIsModalOpen(true) : undefined}
        sx={{ cursor: isTruncated ? "pointer" : "default" }}
      >
        <Typography variant="caption" className="font-medium text-gray-700">
          {variableName}:
        </Typography>
        <Box className="flex items-start gap-1 mt-1">
          <Typography variant="body2" className="text-gray-900 flex-1 break-words">
            {displayValue}
          </Typography>
          {isTruncated && (
            <Tooltip title="View full content">
              <IconButton
                size="small"
                sx={{
                  opacity: 0.5,
                  "&:hover": { opacity: 1 },
                  padding: 0.25,
                  flexShrink: 0,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  setIsModalOpen(true);
                }}
              >
                <OpenInFullIcon sx={{ fontSize: 14 }} />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Box>

      <Dialog
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        maxWidth="md"
        fullWidth
        onClick={(e) => e.stopPropagation()}
      >
        <DialogTitle>
          <Box className="flex justify-between items-start gap-2">
            <Box className="flex-1">
              <Typography variant="h6" gutterBottom>
                {variableName}
              </Typography>
              <Typography variant="caption" className="text-gray-600">
                {value.length.toLocaleString()} characters
              </Typography>
            </Box>
            <IconButton
              size="small"
              onClick={handleCopy}
              title="Copy to clipboard"
              sx={{
                "&:hover": { color: "primary.main" },
                flexShrink: 0,
              }}
            >
              <ContentCopyIcon fontSize="small" />
            </IconButton>
          </Box>
        </DialogTitle>

        <DialogContent dividers>
          <Box
            sx={{
              p: 2,
              bgcolor: "background.default",
              borderRadius: 1,
              fontSize: "0.875rem",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              minHeight: "200px",
              maxHeight: "60vh",
              overflow: "auto",
              border: 1,
              borderColor: "divider",
              lineHeight: 1.6,
            }}
          >
            {value}
          </Box>
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={handleCopy} variant="outlined" size="small">
            Copy
          </Button>
          <Button onClick={() => setIsModalOpen(false)} variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
