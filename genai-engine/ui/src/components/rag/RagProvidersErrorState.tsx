import { Error as ErrorIcon } from "@mui/icons-material";
import { Box, Button, Typography } from "@mui/material";
import React from "react";

interface RagProvidersErrorStateProps {
  error: Error;
  onRetry: () => void;
}

export const RagProvidersErrorState: React.FC<RagProvidersErrorStateProps> = ({
  error,
  onRetry,
}) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "400px",
        gap: 2,
        px: 3,
      }}
    >
      <ErrorIcon sx={{ fontSize: 64, color: "error.main", opacity: 0.7 }} />
      <Typography variant="h6" color="error">
        Failed to Load RAG Providers
      </Typography>
      <Typography variant="body2" color="text.secondary" textAlign="center">
        {error.message || "An unexpected error occurred"}
      </Typography>
      <Button variant="outlined" onClick={onRetry} sx={{ mt: 2 }}>
        Try Again
      </Button>
    </Box>
  );
};

