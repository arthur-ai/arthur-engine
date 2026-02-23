"use client";

import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import React from "react";

import { useTask } from "@/hooks/useTask";

export const TaskDetailContent: React.FC = () => {
  const { task } = useTask();

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
      </Box>
    </Box>
  );
};
