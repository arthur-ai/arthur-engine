import AddIcon from "@mui/icons-material/Add";
import { Box, Button, Typography } from "@mui/material";
import React from "react";

interface PromptExperimentsViewHeaderProps {
  onCreateExperiment: () => void;
}

export const PromptExperimentsViewHeader: React.FC<PromptExperimentsViewHeaderProps> = ({
  onCreateExperiment,
}) => {
  return (
    <Box className="flex justify-between items-center mb-4">
      <Box>
        <Typography variant="h5" className="font-semibold mb-1 text-gray-900">
          Prompt Experiments
        </Typography>
        <Typography variant="body2" className="text-gray-600">
          Test and compare different prompt variations and their effectiveness
        </Typography>
      </Box>
      <Button
        variant="contained"
        color="primary"
        startIcon={<AddIcon />}
        onClick={onCreateExperiment}
      >
        Create Experiment
      </Button>
    </Box>
  );
};
