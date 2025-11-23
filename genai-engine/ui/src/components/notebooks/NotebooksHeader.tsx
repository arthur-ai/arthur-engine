import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import React from "react";

import type { NotebooksHeaderProps } from "./types";

const NotebooksHeader = ({ onCreateNotebook }: NotebooksHeaderProps) => {
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
            Manage and organize your prompt experiment notebooks
          </Typography>
        </Box>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateNotebook}>
          Create Notebook
        </Button>
      </Box>
      <Divider />
    </div>
  );
};

export default NotebooksHeader;

