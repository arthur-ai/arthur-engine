import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import React from "react";

import type { EvalRowExpansionProps } from "../types";

const EvalRowExpansion: React.FC<EvalRowExpansionProps> = ({ eval: evalMetadata, onExpandToFullScreen }) => {
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return dateString;
    }
  };

  return (
    <Box sx={{ p: 2, backgroundColor: "grey.50" }}>
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Versions
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {evalMetadata.versions}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Created At
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {formatDate(evalMetadata.created_at)}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Latest Version Created At
            </Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {formatDate(evalMetadata.latest_version_created_at)}
            </Typography>
          </Box>
          {evalMetadata.deleted_versions.length > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                Deleted Versions
              </Typography>
              <Box sx={{ display: "flex", gap: 0.5, mt: 0.5 }}>
                {evalMetadata.deleted_versions.map((version) => (
                  <Chip key={version} label={`v${version}`} size="small" color="error" sx={{ height: 20, fontSize: "0.75rem" }} />
                ))}
              </Box>
            </Box>
          )}
        </Box>
        <Box>
          <Button variant="outlined" size="small" startIcon={<OpenInFullIcon />} onClick={onExpandToFullScreen}>
            Expand to Full Screen
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default EvalRowExpansion;
