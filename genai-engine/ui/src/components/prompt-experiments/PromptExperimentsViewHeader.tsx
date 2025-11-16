import AddIcon from "@mui/icons-material/Add";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import SearchIcon from "@mui/icons-material/Search";
import { Box, Button, Typography, ButtonGroup, Menu, MenuItem, TextField, InputAdornment } from "@mui/material";
import React, { useState } from "react";

interface PromptExperimentsViewHeaderProps {
  onCreateExperiment: () => void;
  onCreateFromExisting: () => void;
  searchValue: string;
  onSearchChange: (value: string) => void;
}

export const PromptExperimentsViewHeader: React.FC<PromptExperimentsViewHeaderProps> = ({
  onCreateExperiment,
  onCreateFromExisting,
  searchValue,
  onSearchChange,
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleCreateNew = () => {
    handleClose();
    onCreateExperiment();
  };

  const handleCreateFromExisting = () => {
    handleClose();
    onCreateFromExisting();
  };

  return (
    <Box className="flex flex-col gap-4">
      <Box className="flex justify-between items-center">
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
          endIcon={<ArrowDropDownIcon />}
          onClick={handleClick}
          aria-controls={open ? "create-experiment-menu" : undefined}
          aria-haspopup="true"
          aria-expanded={open ? "true" : undefined}
        >
          Create Experiment
        </Button>
        <Menu
          id="create-experiment-menu"
          anchorEl={anchorEl}
          open={open}
          onClose={handleClose}
          anchorOrigin={{
            vertical: "bottom",
            horizontal: "right",
          }}
          transformOrigin={{
            vertical: "top",
            horizontal: "right",
          }}
          slotProps={{
            paper: {
              sx: {
                width: anchorEl?.offsetWidth,
                minWidth: anchorEl?.offsetWidth,
              },
            },
          }}
        >
          <MenuItem onClick={handleCreateNew} sx={{ justifyContent: "flex-start" }}>
            Create New
          </MenuItem>
          <MenuItem onClick={handleCreateFromExisting} sx={{ justifyContent: "flex-start" }} disabled>
            Create from Existing
          </MenuItem>
        </Menu>
      </Box>
      <TextField
        placeholder="Search experiments by name, description, prompt, or dataset..."
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
