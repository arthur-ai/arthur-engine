import CloseIcon from "@mui/icons-material/Close";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import type { EvalDetailViewProps } from "../types";
import NunjucksHighlightedTextField from "../MustacheHighlightedTextField";

import { formatDate } from "@/utils/formatters";

const EvalDetailView = ({ evalData, isLoading, error, evalName, version, onClose }: EvalDetailViewProps) => {
  if (isLoading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "100%",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Error loading eval: {error.message}</Alert>
      </Box>
    );
  }

  if (!evalData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">No eval data available</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, height: "100%", overflow: "auto" }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          {evalName}
          {version !== null && <Chip label={`Version ${version}`} size="small" sx={{ ml: 2, height: 24 }} />}
        </Typography>
        {onClose && (
          <IconButton onClick={onClose} aria-label="Close">
            <CloseIcon />
          </IconButton>
        )}
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Metadata
        </Typography>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Model Provider
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {evalData.model_provider}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Model Name
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {evalData.model_name}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Created At
            </Typography>
            <Typography variant="body1" sx={{ fontWeight: 500 }}>
              {evalData.created_at ? formatDate(evalData.created_at) : "N/A"}
            </Typography>
          </Box>
          {evalData.deleted_at && (
            <Box>
              <Typography variant="caption" color="text.secondary">
                Deleted At
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 500, color: "error.main" }}>
                {formatDate(evalData.deleted_at)}
              </Typography>
            </Box>
          )}
        </Box>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
          Instructions
        </Typography>
        <NunjucksHighlightedTextField
          value={evalData.instructions}
          onChange={() => {}} // Read-only, no-op
          disabled
          multiline
          minRows={4}
          maxRows={20}
          size="small"
        />
      </Paper>

      {evalData.config && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Configuration
          </Typography>
          <Box
            component="pre"
            sx={{
              backgroundColor: "grey.50",
              p: 2,
              borderRadius: 1,
              overflow: "auto",
              fontSize: "0.875rem",
              fontFamily: "monospace",
            }}
          >
            {JSON.stringify(evalData.config, null, 2)}
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default EvalDetailView;
