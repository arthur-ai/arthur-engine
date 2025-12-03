import { Box, Button, Collapse, Paper, Stack, Typography } from "@mui/material";
import { FallbackProps } from "react-error-boundary";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import RefreshIcon from "@mui/icons-material/Refresh";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import { useState } from "react";

interface ErrorFallbackProps extends FallbackProps {
  title?: string;
  description?: string;
}

export const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
  title = "Something went wrong",
  description,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const errorMessage = error?.message || "Unknown error occurred";
  const errorStack = error?.stack;

  return (
    <Box sx={{ p: 3, width: "max-content", mx: "auto" }}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ErrorOutlineIcon color="error" />
            <Typography variant="h6" color="error">
              {title}
            </Typography>
          </Stack>

          {description && (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          )}

          <Typography
            variant="body2"
            component="pre"
            sx={{
              fontFamily: "monospace",
              color: "error.main",
              bgcolor: "action.hover",
              p: 1.5,
              borderRadius: 1,
            }}
          >
            {errorMessage}
          </Typography>

          {errorStack && (
            <Box>
              <Button
                onClick={() => setShowDetails(!showDetails)}
                endIcon={showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                size="small"
                variant="text"
              >
                {showDetails ? "Hide" : "Show"} details
              </Button>
              <Collapse in={showDetails}>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    bgcolor: "grey.900",
                    color: "grey.300",
                    p: 1.5,
                    borderRadius: 1,
                    mt: 1,
                    overflow: "auto",
                    maxHeight: 300,
                  }}
                >
                  {errorStack}
                </Typography>
              </Collapse>
            </Box>
          )}

          {resetErrorBoundary && (
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={resetErrorBoundary}
              sx={{ alignSelf: "flex-start" }}
            >
              Try again
            </Button>
          )}
        </Stack>
      </Paper>
    </Box>
  );
};
