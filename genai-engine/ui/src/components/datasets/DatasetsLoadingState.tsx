import { Box, CircularProgress } from "@mui/material";
import React from "react";

export const DatasetsLoadingState: React.FC = () => {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "400px",
      }}
    >
      <CircularProgress />
    </Box>
  );
};
