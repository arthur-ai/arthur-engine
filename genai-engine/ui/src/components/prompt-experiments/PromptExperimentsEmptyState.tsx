import AddIcon from "@mui/icons-material/Add";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import { Box, Button, Typography } from "@mui/material";
import React from "react";

interface PromptExperimentsEmptyStateProps {
  onCreateExperiment: () => void;
}

export const PromptExperimentsEmptyState: React.FC<PromptExperimentsEmptyStateProps> = ({ onCreateExperiment }) => {
  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        textAlign: "center",
        py: 8,
      }}
    >
      <ScienceOutlinedIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 500, color: "text.primary" }}>
        No experiments yet
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Get started by creating your first experiment
      </Typography>
      <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateExperiment} size="large">
        Experiment
      </Button>
    </Box>
  );
};
