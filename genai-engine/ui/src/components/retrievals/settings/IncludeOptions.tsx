import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import Typography from "@mui/material/Typography";
import React from "react";

interface IncludeOptionsProps {
  includeMetadata: boolean;
  includeVector: boolean;
  onIncludeMetadataChange: (checked: boolean) => void;
  onIncludeVectorChange: (checked: boolean) => void;
  isExecuting: boolean;
}

export const IncludeOptions: React.FC<IncludeOptionsProps> = React.memo(
  ({ includeMetadata, includeVector, onIncludeMetadataChange, onIncludeVectorChange, isExecuting }) => {
    return (
      <Box>
        <Typography variant="body2" sx={{ fontWeight: 500, color: "text.primary", mb: 1.5 }}>
          Include in Results
        </Typography>
        <FormGroup>
          <FormControlLabel
            control={
              <Checkbox checked={includeMetadata} onChange={(e) => onIncludeMetadataChange(e.target.checked)} disabled={isExecuting} size="small" />
            }
            label={
              <Typography variant="body2" sx={{ color: "text.primary" }}>
                Metadata (distance, score, explainScore)
              </Typography>
            }
          />
          <FormControlLabel
            control={
              <Checkbox checked={includeVector} onChange={(e) => onIncludeVectorChange(e.target.checked)} disabled={isExecuting} size="small" />
            }
            label={
              <Typography variant="body2" sx={{ color: "text.primary" }}>
                Vector embeddings
              </Typography>
            }
          />
        </FormGroup>
      </Box>
    );
  }
);
