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
          <Typography variant="h5" className="font-semibold mb-1 text-gray-900 dark:text-gray-100">
            RAG Experiments
          </Typography>
          <Typography variant="body2" className="text-gray-600 dark:text-gray-400">
            View and compare results from RAG configuration experiments
          </Typography>
        </Box>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateExperiment}>
          New Experiment
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
