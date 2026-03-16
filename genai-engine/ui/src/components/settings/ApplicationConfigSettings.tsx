import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
  Typography,
} from "@mui/material";
import { useSnackbar } from "notistack";
import React, { useCallback } from "react";

import { useApplicationConfiguration } from "@/hooks/useApplicationConfiguration";

const ALLOWED_TRACE_RETENTION_DAYS = [7, 14, 30, 90, 120, 365] as const;

export const ApplicationConfigSettings: React.FC = () => {
  const { data, isLoading, error, updateConfiguration } = useApplicationConfiguration();
  const { enqueueSnackbar } = useSnackbar();

  const handleTraceRetentionChange = useCallback(
    async (event: SelectChangeEvent<number>) => {
      const value = event.target.value as (typeof ALLOWED_TRACE_RETENTION_DAYS)[number];
      if (!Number.isInteger(value) || !ALLOWED_TRACE_RETENTION_DAYS.includes(value)) return;
      try {
        await updateConfiguration({ trace_retention_days: value });
        enqueueSnackbar("Application configuration updated", { variant: "success" });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to update configuration";
        enqueueSnackbar(message, { variant: "error" });
      }
    },
    [updateConfiguration, enqueueSnackbar],
  );

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Failed to load application configuration: {error instanceof Error ? error.message : String(error)}
      </Alert>
    );
  }

  const traceRetentionDays = data?.trace_retention_days ?? 90;

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Application configuration
      </Typography>
      <Card variant="outlined" sx={{ maxWidth: 480 }}>
        <CardContent>
          <FormControl fullWidth variant="filled" sx={{ mt: 1, mb: 1 }}>
            <InputLabel id="trace-retention-label">Trace retention (days)</InputLabel>
            <Select
              labelId="trace-retention-label"
              id="trace-retention-days"
              value={traceRetentionDays}
              label="Trace retention (days)"
              onChange={handleTraceRetentionChange}
            >
              {ALLOWED_TRACE_RETENTION_DAYS.map((days) => (
                <MenuItem key={days} value={days}>
                  {days} days
                </MenuItem>
              ))}
            </Select>
            <Typography variant="caption" sx={{ mt: 1, display: "block", color: "text.secondary" }}>
              Traces older than this many days are automatically deleted.
            </Typography>
          </FormControl>
        </CardContent>
      </Card>
    </Box>
  );
};
