import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import React from "react";

import type { PromptsManagementHeaderProps } from "./types";

const PromptsManagementHeader = ({ onCreatePrompt }: PromptsManagementHeaderProps) => {
  return (
    <div>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          p: 2,
          backgroundColor: "white",
        }}
      >
        <Box>
          <Typography variant="subtitle1" color="text.primary">
            Manage and organize your prompts
          </Typography>
        </Box>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreatePrompt}>
          New Prompt
        </Button>
      </Box>
      <Divider />
    </div>
  );
};

export default PromptsManagementHeader;
