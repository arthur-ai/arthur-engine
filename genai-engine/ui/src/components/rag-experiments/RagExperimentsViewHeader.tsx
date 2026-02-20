import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import { Box, Button, Typography, TextField, InputAdornment } from "@mui/material";
import React from "react";

interface RagExperimentsViewHeaderProps {
  onCreateExperiment: () => void;
  searchValue: string;
  onSearchChange: (value: string) => void;
}

export const RagExperimentsViewHeader: React.FC<RagExperimentsViewHeaderProps> = ({ onCreateExperiment, searchValue, onSearchChange }) => {
  return (
    <Box className="flex flex-col gap-4">
      <Box className="flex justify-between items-center">
        <Box>
          <Typography variant="h5" fontWeight={600} color="text.primary">
            RAG Experiments
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            View and compare results from RAG configuration experiments
          </Typography>
        </Box>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateExperiment}>
          Experiment
        </Button>
      </Box>
      <TextField
        placeholder="Search experiments by name, description, or dataset..."
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        fullWidth
        size="small"
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          },
        }}
      />
    </Box>
  );
};
