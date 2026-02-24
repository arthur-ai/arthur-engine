"use client";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { useSnackbar } from "notistack";
import React, { useState } from "react";

import { useApplicationConfiguration } from "@/hooks/useApplicationConfiguration";
import { useTask } from "@/hooks/useTask";

const TRACE_RETENTION_OPTIONS = [
  { value: 7, label: "7 days" },
  { value: 14, label: "14 days" },
  { value: 30, label: "30 days" },
  { value: 90, label: "90 days" },
  { value: 120, label: "120 days" },
  { value: 365, label: "365 days" },
] as const;

export const TaskDetailContent: React.FC = () => {
  const { task } = useTask();
  const { data: config, isLoading: configLoading, updateConfiguration } = useApplicationConfiguration();
  const [updating, setUpdating] = useState(false);
  const { enqueueSnackbar } = useSnackbar();

  const handleRetentionChange = async (days: number) => {
    try {
      setUpdating(true);
      await updateConfiguration({ trace_retention_days: days });
      enqueueSnackbar("Trace retention updated", { variant: "success" });
    } catch (err) {
      enqueueSnackbar(
        err instanceof Error ? err.message : "Failed to update retention",
        { variant: "error" }
      );
    } finally {
      setUpdating(false);
    }
  };

  if (!task) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", height: 256 }}>
        <CircularProgress />
      </Box>
    );
  }
  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Box>
          <Typography variant="h5" fontWeight={600} color="text.primary">
            Task Details
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            View task configuration and metadata
          </Typography>
        </Box>
      </Box>

      <Box sx={{ p: 3 }}>
        <Paper variant="outlined">
          <Box sx={{ px: 3, py: 2, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <Typography variant="subtitle1" fontWeight={500} color="text.primary">
              {task.name || "Untitled Task"}
            </Typography>
            {task.is_agentic && <Chip label="Agentic" size="small" color="primary" variant="outlined" />}
          </Box>
          <Divider />
          <Box sx={{ px: 3, py: 2 }}>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, gap: 3 }}>
              <Box>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Task ID
                </Typography>
                <Typography variant="body2" color="text.primary" sx={{ mt: 0.5, fontFamily: "monospace" }}>
                  {task.id}
                </Typography>
              </Box>

              {task.is_agentic !== undefined && (
                <Box>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    Type
                  </Typography>
                  <Typography variant="body2" color="text.primary" sx={{ mt: 0.5 }}>
                    {task.is_agentic ? "Agentic Task" : "Standard Task"}
                  </Typography>
                </Box>
              )}

              <Box>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Created At
                </Typography>
                <Typography variant="body2" color="text.primary" sx={{ mt: 0.5 }}>
                  {task.created_at ? new Date(task.created_at).toLocaleString() : "Not available"}
                </Typography>
              </Box>

              <Box>
                <Typography variant="body2" color="text.secondary" fontWeight={500}>
                  Updated At
                </Typography>
                <Typography variant="body2" color="text.primary" sx={{ mt: 0.5 }}>
                  {task.updated_at ? new Date(task.updated_at).toLocaleString() : "Not available"}
                </Typography>
              </Box>
            </Box>
          </Box>
        </Paper>

        <Card variant="outlined" sx={{ mt: 3, bgcolor: "background.paper" }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
              Trace data retention
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Traces older than the selected period are automatically deleted. This setting applies to all tasks.
            </Typography>
            <FormControl size="small" variant="filled" sx={{ minWidth: 160 }} disabled={configLoading || updating}>
              <InputLabel id="trace-retention-label">Retention period</InputLabel>
              <Select
                labelId="trace-retention-label"
                value={config?.trace_retention_days ?? 90}
                label="Retention period"
                onChange={(e) => handleRetentionChange(Number(e.target.value))}
              >
                {TRACE_RETENTION_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
};
