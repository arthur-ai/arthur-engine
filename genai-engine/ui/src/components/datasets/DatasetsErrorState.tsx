import { Alert, Box, Button } from "@mui/material";
import React from "react";

interface DatasetsErrorStateProps {
  error: Error;
  onRetry: () => void;
}

export const DatasetsErrorState: React.FC<DatasetsErrorStateProps> = ({
  error,
  onRetry,
}) => {
  return (
    <Box sx={{ p: 3 }}>
      <Alert
        severity="error"
        action={
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        }
      >
        {error.message || "Failed to load datasets. Please try again."}
      </Alert>
    </Box>
  );
};
