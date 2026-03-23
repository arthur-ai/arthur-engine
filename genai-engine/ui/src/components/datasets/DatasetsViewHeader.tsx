import AddIcon from "@mui/icons-material/Add";
import { Box, Button, Typography } from "@mui/material";
import React from "react";

interface DatasetsViewHeaderProps {
  onCreateDataset: () => void;
}

export const DatasetsViewHeader: React.FC<DatasetsViewHeaderProps> = ({ onCreateDataset }) => {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <Box>
        <Typography variant="h5" fontWeight={600} color="text.primary">
          Datasets
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Manage and organize your training and evaluation datasets
        </Typography>
      </Box>
      <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateDataset}>
        Dataset
      </Button>
    </Box>
  );
};
