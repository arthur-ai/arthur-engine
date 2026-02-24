"use client";

import React, { useState } from "react";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Typography from "@mui/material/Typography";
import { useSnackbar } from "notistack";

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
      enqueueSnackbar(err instanceof Error ? err.message : "Failed to update retention", { variant: "error" });
    } finally {
      setUpdating(false);
    }
  };

  if (!task) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  return (
    <div className="py-6 px-6">
      <div className="bg-white dark:bg-gray-900 shadow dark:shadow-gray-900/50 rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">{task.name || "Untitled Task"}</h2>
            <div className="flex items-center space-x-2">
              {task.is_agentic && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                  Agentic
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="px-6 py-4">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Task ID</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100 font-mono">{task.id}</dd>
            </div>

            {task.is_agentic !== undefined && (
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Type</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{task.is_agentic ? "Agentic Task" : "Standard Task"}</dd>
              </div>
            )}

            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Created At</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                {task.created_at ? new Date(task.created_at).toLocaleString() : "Not available"}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Updated At</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                {task.updated_at ? new Date(task.updated_at).toLocaleString() : "Not available"}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <Box sx={{ mt: 3 }}>
        <Card variant="outlined" sx={{ bgcolor: "background.paper" }}>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
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
    </div>
  );
};
