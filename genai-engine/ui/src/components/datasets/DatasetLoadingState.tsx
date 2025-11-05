import { Box, CircularProgress, Typography } from "@mui/material";
import React from "react";

interface DatasetLoadingStateProps {
  type: "full" | "inline";
  message?: string;
}

export const DatasetLoadingState: React.FC<DatasetLoadingStateProps> = ({
  type,
  message,
}) => {
  if (type === "full") {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "400px",
          gap: 2,
        }}
      >
        <CircularProgress />
        {message && (
          <Typography variant="body2" color="text.secondary">
            {message}
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
      <CircularProgress size={24} />
    </Box>
  );
};
