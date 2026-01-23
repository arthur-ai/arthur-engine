import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import React from "react";

import type { RagNotebooksHeaderProps } from "./types";

const RagNotebooksHeader: React.FC<RagNotebooksHeaderProps> = ({ onCreateNotebook }) => {
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
          <Typography variant="h5" className="font-semibold mb-1 text-gray-900">
            RAG Notebooks
          </Typography>
          <Typography variant="body2" className="text-gray-600">
            Manage and organize your RAG experiment notebooks
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

export default RagNotebooksHeader;
