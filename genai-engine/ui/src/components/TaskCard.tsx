import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CheckIcon from "@mui/icons-material/Check";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import GeneratingTokensOutlinedIcon from "@mui/icons-material/GeneratingTokensOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import { Box, Card, CardContent, Chip, Stack, Tooltip, Typography } from "@mui/material";
import { keyframes } from "@mui/system";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { CopyableChip } from "./common";

import { useTaskMetrics } from "@/hooks/tasks/useTaskMetrics";
import { TaskResponse } from "@/lib/api";

interface TaskCardProps {
  task: TaskResponse;
}

export const TaskCard: React.FC<TaskCardProps> = ({ task }) => {
  const navigate = useNavigate();
  const [copiedTaskId, setCopiedTaskId] = useState<string | null>(null);

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

  const handleTaskClick = () => {
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
    <Card
      onClick={handleTaskClick}
      sx={{
        cursor: "pointer",
        transition: "all 0.2s",
        border: "1px solid",
        borderColor: "divider",
        "&:hover": {
          borderColor: "primary.main",
          boxShadow: 3,
          background: "linear-gradient(to bottom right, rgba(59, 130, 246, 0.03), transparent)",
          "& .view-traces-text": {
            opacity: 1,
          },
        },
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
                      bgcolor: "grey.100",
                      color: "grey.700",
                      "& .MuiChip-icon": {
                        fontSize: 16,
                        color: "grey.600",
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
                      bgcolor: "primary.50",
                      color: "primary.dark",
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
              bgcolor: "grey.50",
              borderRadius: 1,
              border: 1,
              borderColor: "grey.100",
              overflow: "hidden",
            }}
          >
            <Tooltip title="Total traces recorded in the last 7 days" arrow placement="top">
              <Box sx={{ flex: 1, p: 1.5, textAlign: "center", borderRight: 1, borderColor: "grey.200" }}>
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
              <Box sx={{ flex: 1, p: 1.5, textAlign: "center", borderRight: 1, borderColor: "grey.200" }}>
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
                  bgcolor: metrics.successRate >= 1 && metrics.successRate < 50 ? "error.50" : "transparent",
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
              <Typography variant="caption" sx={{ display: "block", fontWeight: 500, color: metrics.lastActive ? "text.primary" : "text.disabled" }}>
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
              borderColor: "grey.100",
              mt: "auto",
            }}
          >
            <Typography
              className="view-traces-text"
              variant="body2"
              color="primary"
              sx={{
                fontWeight: 500,
                opacity: 0,
                transition: "opacity 0.15s",
              }}
            >
              View traces →
            </Typography>
            <Box sx={{ position: "relative" }}>
              {copiedTaskId === task.id ? (
                <Box
                  sx={{
                    bgcolor: "success.50",
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
                    backgroundColor: "#F9FAFB",
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
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
};
