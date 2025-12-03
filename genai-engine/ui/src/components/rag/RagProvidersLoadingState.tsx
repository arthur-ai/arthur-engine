import { Box, CircularProgress, Typography } from "@mui/material";
import React from "react";

export const RagProvidersLoadingState: React.FC = () => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "400px",
        gap: 2,
      }}
    >
      <CircularProgress />
      <Typography variant="body1" color="text.secondary">
        Loading RAG providers...
      </Typography>
    </Box>
  );
};

