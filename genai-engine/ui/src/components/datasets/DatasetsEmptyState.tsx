import AddIcon from "@mui/icons-material/Add";
import FolderOpenIcon from "@mui/icons-material/FolderOpen";
import SearchIcon from "@mui/icons-material/Search";
import { Box, Button, Typography } from "@mui/material";
import React from "react";

interface DatasetsEmptyStateProps {
  type: "no-datasets" | "no-results";
  onCreateDataset?: () => void;
}

export const DatasetsEmptyState: React.FC<DatasetsEmptyStateProps> = ({
  type,
  onCreateDataset,
}) => {
  if (type === "no-datasets") {
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          textAlign: "center",
          py: 4,
        }}
      >
        <FolderOpenIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
        <Typography
          variant="h5"
          gutterBottom
          sx={{ fontWeight: 500, color: "text.primary" }}
        >
          No datasets yet
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Get started by creating your first dataset
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={onCreateDataset}
          size="large"
        >
          Create Dataset
        </Button>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        textAlign: "center",
        py: 4,
      }}
    >
      <SearchIcon sx={{ fontSize: 64, color: "text.primary", mb: 2 }} />
      <Typography variant="h6" gutterBottom>
        No datasets found
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Try adjusting your search query
      </Typography>
    </Box>
  );
};
