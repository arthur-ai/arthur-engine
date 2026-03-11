import AddIcon from "@mui/icons-material/Add";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import Typography from "@mui/material/Typography";
import React from "react";

import type { EvaluatorsHeaderProps } from "./types";

const EvaluatorsHeader = ({ onCreateEval }: EvaluatorsHeaderProps) => {
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
            Evals Management
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Manage and organize your evaluation metrics
          </Typography>
        </Box>
        <Button variant="contained" color="primary" startIcon={<AddIcon />} onClick={onCreateEval}>
          Evaluator
        </Button>
      </Box>
      <Divider />
    </div>
  );
};

export default EvaluatorsHeader;
