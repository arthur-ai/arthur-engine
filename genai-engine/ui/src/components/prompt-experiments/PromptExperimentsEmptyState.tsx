import AddIcon from "@mui/icons-material/Add";
import ScienceIcon from "@mui/icons-material/Science";
import { Box, Button, Typography } from "@mui/material";
import React from "react";

interface PromptExperimentsEmptyStateProps {
  onCreateExperiment: () => void;
}

export const PromptExperimentsEmptyState: React.FC<PromptExperimentsEmptyStateProps> = ({
  onCreateExperiment,
}) => {
  return (
    <Box className="flex flex-col items-center justify-center h-full text-center py-8">
      <ScienceIcon className="text-6xl text-gray-500 mb-4" />
      <Typography variant="h5" className="font-medium text-gray-900 mb-2">
        No experiments yet
      </Typography>
      <Typography variant="body1" className="text-gray-600 mb-6">
        Get started by creating your first experiment
      </Typography>
      <Button
        variant="contained"
        color="primary"
        startIcon={<AddIcon />}
        onClick={onCreateExperiment}
        size="large"
      >
        Create Experiment
      </Button>
    </Box>
  );
};
