import ArchiveOutlinedIcon from "@mui/icons-material/ArchiveOutlined";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckIcon from "@mui/icons-material/Check";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import GeneratingTokensOutlinedIcon from "@mui/icons-material/GeneratingTokensOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import UnarchiveOutlinedIcon from "@mui/icons-material/UnarchiveOutlined";
import { Box, Card, CardContent, Chip, CircularProgress, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { CopyableChip } from "./common";

import { useTaskMetrics } from "@/hooks/tasks/useTaskMetrics";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";

interface TaskCardProps {
  task: TaskResponse;
  onArchiveToggle?: () => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({ task, onArchiveToggle }) => {
  const navigate = useNavigate();
  const api = useApi();
  const [copiedTaskId, setCopiedTaskId] = useState<string | null>(null);
  const [isArchiving, setIsArchiving] = useState(false);

  const { data: metrics = { traceCount: 0, totalTokens: 0, successRate: 0, lastActive: null } } = useTaskMetrics(task.id);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatLastActive = (lastActive: string | null) => {
    if (!lastActive) return "Inactive";

    const now = new Date();
    const lastActiveDate = new Date(lastActive);

    // Handle invalid dates
    if (isNaN(lastActiveDate.getTime())) return "Inactive";

    const diffMs = now.getTime() - lastActiveDate.getTime();

    // Handle future dates (clock skew)
    if (diffMs < 0) return "Just now";

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins} min${diffMins === 1 ? "" : "s"} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  };

  const handleArchiveToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!api || isArchiving) return;

    try {
      setIsArchiving(true);
      if (task.is_archived) {
        await api.api.unarchiveTaskApiV2TasksTaskIdUnarchivePost(task.id);
      } else {
        await api.api.archiveTaskApiV2TasksTaskIdDelete(task.id);
      }
      onArchiveToggle?.();
    } catch (err) {
      console.error("Failed to toggle archive status:", err);
    } finally {
      setIsArchiving(false);
    }
  };

  const handleTaskClick = () => {
    if (task.is_archived) return;
    navigate(`/tasks/${task.id}/traces`);
  };

  const fadeIn = keyframes`
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  `;

  return (
    <Tooltip title={task.is_archived ? "This task is archived. Unarchive it to view its traces." : ""} placement="top" arrow>
      <Box component="span">
        <Card
          onClick={handleTaskClick}
          sx={{
            cursor: task.is_archived ? "not-allowed" : "pointer",
            transition: "all 0.2s",
            border: "1px solid",
            borderColor: "divider",
            opacity: task.is_archived ? 0.6 : 1,
            ...(!task.is_archived && {
              "&:hover": {
                borderColor: "primary.main",
                boxShadow: 3,
                background: "linear-gradient(to bottom right, rgba(59, 130, 246, 0.03), transparent)",
                "& .view-traces-text": {
                  opacity: 1,
                },
              },
            }),
          }}
        >
          <CardContent sx={{ p: 2.5, height: "100%", display: "flex", flexDirection: "column" }}>
            <Stack spacing={2} sx={{ height: "100%" }}>
              {/* Header with badge */}
              <Box sx={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 1 }}>
                <Typography
                  variant="subtitle1"
                  sx={{
                    fontWeight: 600,
                    lineHeight: 1.3,
                    flex: 1,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {task.name}
                </Typography>
                <Stack direction="row" spacing={0.5} sx={{ flexShrink: 0 }}>
                  {task.is_system_task && (
                    <Tooltip title="System Task - Managed by Arthur" arrow placement="top">
                      <Chip
                        icon={<SettingsIcon />}
                        size="small"
                        sx={{
                          height: 24,
                          bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.100"),
                          color: (theme) => (theme.palette.mode === "dark" ? "grey.300" : "grey.700"),
                          "& .MuiChip-icon": {
                            fontSize: 16,
                            color: (theme) => (theme.palette.mode === "dark" ? "grey.400" : "grey.600"),
                            ml: 0.5,
                          },
                          "& .MuiChip-label": {
                            px: 0.5,
                          },
                        }}
                      />
                    </Tooltip>
                  )}
                  {task.is_autocreated && (
                    <Tooltip title="Auto-created - Created automatically by Arthur" arrow placement="top">
                      <Chip
                        icon={<AutoAwesomeIcon />}
                        size="small"
                        sx={{
                          height: 24,
                          bgcolor: (theme) => (theme.palette.mode === "dark" ? "rgba(99, 102, 241, 0.15)" : "primary.50"),
                          color: (theme) => (theme.palette.mode === "dark" ? "primary.light" : "primary.dark"),
                          "& .MuiChip-icon": {
                            fontSize: 16,
                            color: "primary.main",
                            ml: 0.5,
                          },
                          "& .MuiChip-label": {
                            px: 0.5,
                          },
                        }}
                      />
                    </Tooltip>
                  )}
                </Stack>
              </Box>

              {/* Metrics */}
              <Box
                sx={{
                  display: "flex",
                  bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.900" : "grey.50"),
                  borderRadius: 1,
                  border: 1,
                  borderColor: "divider",
                  overflow: "hidden",
                }}
              >
                <Tooltip title="Total traces recorded in the last 7 days" arrow placement="top">
                  <Box sx={{ flex: 1, p: 1.5, textAlign: "center", borderRight: 1, borderColor: "divider" }}>
                    <TrendingUpIcon sx={{ fontSize: 20, color: "primary.main", mb: 0.5 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {formatNumber(metrics.traceCount)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                      Traces
                    </Typography>
                  </Box>
                </Tooltip>
                <Tooltip title="Total tokens consumed in the last 7 days" arrow placement="top">
                  <Box sx={{ flex: 1, p: 1.5, textAlign: "center", borderRight: 1, borderColor: "divider" }}>
                    <GeneratingTokensOutlinedIcon sx={{ fontSize: 20, color: "#A855F7", mb: 0.5 }} />
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                      {formatNumber(metrics.totalTokens)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                      Tokens
                    </Typography>
                  </Box>
                </Tooltip>
                <Tooltip
                  title={
                    metrics.successRate >= 1 && metrics.successRate < 50
                      ? "Warning: Low success rate in the last 7 days. This task needs attention."
                      : "Successful completion rate over the last 7 days"
                  }
                  arrow
                  placement="top"
                >
                  <Box
                    sx={{
                      flex: 1,
                      p: 1.5,
                      textAlign: "center",
                      bgcolor: (theme) =>
                        metrics.successRate >= 1 && metrics.successRate < 50
                          ? theme.palette.mode === "dark"
                            ? "rgba(239, 68, 68, 0.1)"
                            : "error.50"
                          : "transparent",
                    }}
                  >
                    {metrics.successRate >= 1 && metrics.successRate < 50 ? (
                      <ErrorOutlineIcon sx={{ fontSize: 20, color: "error.main", mb: 0.5 }} />
                    ) : (
                      <CheckCircleIcon sx={{ fontSize: 20, color: "success.main", mb: 0.5 }} />
                    )}
                    <Typography
                      variant="h6"
                      sx={{
                        fontWeight: 600,
                        color: metrics.successRate >= 1 && metrics.successRate < 50 ? "error.main" : "text.primary",
                      }}
                    >
                      {metrics.successRate}%
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        mt: 0.5,
                        color: metrics.successRate >= 1 && metrics.successRate < 50 ? "error.main" : "text.secondary",
                      }}
                    >
                      Success
                    </Typography>
                  </Box>
                </Tooltip>
              </Box>

              {/* Metadata */}
              <Stack direction="row" spacing={4}>
                <Box>
                  <Typography variant="caption" color="text.disabled">
                    Last active
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{ display: "block", fontWeight: 500, color: metrics.lastActive ? "text.primary" : "text.disabled" }}
                  >
                    {formatLastActive(metrics.lastActive)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.disabled">
                    Created
                  </Typography>
                  <Typography variant="caption" sx={{ display: "block", fontWeight: 500, color: "text.primary" }}>
                    {new Date(task.created_at).toLocaleDateString()}
                  </Typography>
                </Box>
              </Stack>

              {/* Footer */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  pt: 1.5,
                  borderTop: 1,
                  borderColor: "divider",
                  mt: "auto",
                }}
              >
                <Typography
                  className="view-traces-text"
                  variant="body2"
                  color="primary"
                  sx={{
                    fontWeight: 500,
                    opacity: task.is_archived ? 0 : undefined,
                    transition: "opacity 0.15s",
                  }}
                >
                  {task.is_archived ? "" : "View traces →"}
                </Typography>
                <Stack direction="row" spacing={0.5} alignItems="center">
                  <Box sx={{ position: "relative" }}>
                    {copiedTaskId === task.id ? (
                      <Box
                        sx={{
                          bgcolor: (theme) => (theme.palette.mode === "dark" ? "rgba(34, 197, 94, 0.1)" : "success.50"),
                          border: 1,
                          borderColor: "success.light",
                          borderRadius: 1,
                          px: 1.5,
                          py: 0.5,
                          display: "flex",
                          alignItems: "center",
                          gap: 0.75,
                          animation: `${fadeIn} 0.2s ease-in`,
                        }}
                      >
                        <CheckIcon sx={{ fontSize: 14, color: "success.main" }} />
                        <Typography variant="caption" sx={{ color: "success.dark", fontWeight: 500 }}>
                          Copied!
                        </Typography>
                      </Box>
                    ) : (
                      <CopyableChip
                        label={task.id}
                        size="small"
                        onCopy={() => {
                          setCopiedTaskId(task.id);
                          setTimeout(() => setCopiedTaskId(null), 2000);
                        }}
                        sx={{
                          maxWidth: "140px",
                          height: "24px",
                          fontSize: "0.6875rem",
                          bgcolor: (theme) => (theme.palette.mode === "dark" ? "grey.800" : "grey.50"),
                          "& .MuiChip-label": {
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                            px: 1,
                          },
                          "& .MuiChip-icon": {
                            fontSize: "0.875rem",
                            ml: 0.5,
                          },
                        }}
                      />
                    )}
                  </Box>
                  {!task.is_system_task && (
                    <Tooltip title={task.is_archived ? "Unarchive task" : "Archive task"} arrow placement="top">
                      <IconButton
                        size="small"
                        onClick={handleArchiveToggle}
                        disabled={isArchiving}
                        sx={{
                          color: "text.disabled",
                          "&:hover": { color: task.is_archived ? "success.main" : "error.main" },
                        }}
                      >
                        {isArchiving ? (
                          <CircularProgress size={16} />
                        ) : task.is_archived ? (
                          <UnarchiveOutlinedIcon sx={{ fontSize: 18 }} />
                        ) : (
                          <ArchiveOutlinedIcon sx={{ fontSize: 18 }} />
                        )}
                      </IconButton>
                    </Tooltip>
                  )}
                </Stack>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </Tooltip>
  );
};
