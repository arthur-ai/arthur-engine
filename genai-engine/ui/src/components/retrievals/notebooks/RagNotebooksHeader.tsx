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
          px: 3,
          pt: 3,
          pb: 2,
          backgroundColor: "background.paper",
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={600} color="text.primary">
            RAG Notebooks
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Manage and organize your RAG experiment notebooks
          </Typography>
        </Box>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateNotebook}>
          Notebook
        </Button>
      </Box>
      <Divider />
    </div>
  );
};

export default RagNotebooksHeader;
