import AddIcon from "@mui/icons-material/Add";
import CheckIcon from "@mui/icons-material/Check";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import GeneratingTokensOutlinedIcon from "@mui/icons-material/GeneratingTokensOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { CopyableChip } from "./common";
import { CreateTaskForm } from "./CreateTaskForm";

import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";

interface TaskMetrics {
  traceCount: number;
  totalTokens: number;
  successRate: number;
  lastActive: string | null;
}

export const AllTasks: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const api = useApi();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [taskMetrics, setTaskMetrics] = useState<Record<string, TaskMetrics>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [copiedTaskId, setCopiedTaskId] = useState<string | null>(null);

  useEffect(() => {
    const fetchTaskMetrics = async (taskId: string): Promise<TaskMetrics> => {
      if (!api) {
        return { traceCount: 0, totalTokens: 0, successRate: 0, lastActive: null };
      }

      try {
        // Get traces from last 7 days
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        const response = await api.api.listTracesMetadataApiV1TracesGet({
          task_ids: [taskId],
          start_time: sevenDaysAgo.toISOString(),
          page_size: 5000, // Get all traces for accurate metrics
          page: 0,
        });

        const traces = response.data.traces || [];
        const traceCount = response.data.count || 0;

        // Calculate total tokens
        const totalTokens = traces.reduce((sum, trace) => {
          return sum + (trace.total_token_count || 0);
        }, 0);

        // Calculate success rate (traces without errors)
        // We'll consider a trace successful if it completed (has end_time)
        const successfulTraces = traces.filter((trace) => trace.end_time).length;
        const successRate = traceCount > 0 ? Math.round((successfulTraces / traceCount) * 100) : 0;

        // Find the most recent trace end_time for last active
        let lastActive: string | null = null;
        if (traces.length > 0) {
          for (const trace of traces) {
            const traceDate = trace.end_time || trace.created_at;
            if (traceDate) {
              if (!lastActive || new Date(traceDate) > new Date(lastActive)) {
                lastActive = traceDate;
              }
            }
          }
        }

        return { traceCount, totalTokens, successRate, lastActive };
      } catch (err) {
        console.error(`Failed to fetch metrics for task ${taskId}:`, err);
        return { traceCount: 0, totalTokens: 0, successRate: 0, lastActive: null };
      }
    };

    const fetchTasks = async () => {
      try {
        setIsLoading(true);
        setError(null);

        if (!api) {
          throw new Error("API client not available");
        }

        const response = await api.api.searchTasksApiV2TasksSearchPost(
          {
            page_size: 50,
            page: 0,
          },
          {}
        );

        const fetchedTasks = response.data.tasks || [];
        setTasks(fetchedTasks);

        // Fetch metrics for each task
        const metricsPromises = fetchedTasks.map(async (task) => {
          const metrics = await fetchTaskMetrics(task.id);
          return { taskId: task.id, metrics };
        });

        const metricsResults = await Promise.all(metricsPromises);
        const metricsMap = metricsResults.reduce(
          (acc, { taskId, metrics }) => {
            acc[taskId] = metrics;
            return acc;
          },
          {} as Record<string, TaskMetrics>
        );

        setTaskMetrics(metricsMap);
      } catch (err) {
        console.error("Failed to fetch tasks:", err);
        setError("Failed to load tasks. Please check your authentication.");
      } finally {
        setIsLoading(false);
      }
    };

    if (api) {
      fetchTasks();
    }
  }, [api]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (isMenuOpen) {
        const target = event.target as Element;
        if (!target.closest(".relative")) {
          setIsMenuOpen(false);
        }
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  const handleLogout = () => {
    logout();
  };

  const handleTaskClick = (taskId: string) => {
    navigate(`/tasks/${taskId}/overview`);
  };

  const handleTaskCreated = async (taskId: string) => {
    // Refresh the tasks list
    const fetchTasks = async () => {
      try {
        if (!api) {
          throw new Error("API client not available");
        }

        const response = await api.api.searchTasksApiV2TasksSearchPost(
          {
            page_size: 50,
            page: 0,
          },
          {}
        );

        setTasks(response.data.tasks || []);
      } catch (err) {
        console.error("Failed to fetch tasks:", err);
        setError("Failed to load tasks. Please check your authentication.");
      }
    };

    await fetchTasks();

    // Navigate to the new task
    navigate(`/tasks/${taskId}/overview`);
  };

  return (
    <>
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-3">
            <div className="flex flex-col items-start">
              <img src="/Arthur_Logo_PBW.svg" alt="Arthur" className="h-20 -ml-5" />
            </div>
            <div className="flex items-center space-x-4">
              {tasks.length > 0 && (
                <Button variant="contained" onClick={() => setShowCreateForm(true)} startIcon={<AddIcon />}>
                  Create Task
                </Button>
              )}
              &nbsp;
              <div className="relative">
                <IconButton
                  aria-label="menu"
                  onClick={() => setIsMenuOpen((prev) => !prev)}
                  sx={{
                    backgroundColor: "white",
                    border: "1px solid #e0e0e0",
                    borderRadius: "4px",
                    padding: "8px",
                    width: "40px",
                    height: "40px",
                  }}
                >
                  <MenuIcon />
                </IconButton>
                {/* Dropdown menu */}
                {isMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg py-1 z-50 border border-gray-200">
                    <Button variant="text" onClick={handleLogout} fullWidth sx={{ color: "black" }}>
                      Logout
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-3 sm:px-6 lg:px-8">
        <div className="px-4 py-3 sm:px-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex">
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error loading tasks</h3>
                  <div className="mt-2 text-sm text-red-700">
                    <p>{error}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-gray-500 text-lg font-medium mb-2">No tasks found</div>
              <p className="text-gray-400 mb-8">Get started by creating your first agent task.</p>
              <CreateTaskForm embedded={true} onTaskCreated={handleTaskCreated} onCancel={() => {}} />
            </div>
          ) : (
            <>
              <div className="mb-4">
                <h2 className="text-lg font-medium text-gray-900">All Tasks ({tasks.length})</h2>
                <div className="flex justify-between items-center mt-2">
                  <p className="text-sm text-gray-500">Click on any task to open the toolkit</p>
                  <div className="flex items-center text-gray-500 text-sm">
                    <ShowChartIcon sx={{ fontSize: 18, mr: 0.5 }} />
                    <span>Metrics from last 7 days</span>
                  </div>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {tasks.map((task) => {
                  const metrics = taskMetrics[task.id] || { traceCount: 0, totalTokens: 0, successRate: 0, lastActive: null };
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

                  return (
                    <div
                      key={task.id}
                      onClick={() => handleTaskClick(task.id)}
                      className="group bg-white border border-gray-200 rounded-lg cursor-pointer hover:border-blue-500 hover:shadow-lg hover:bg-gradient-to-br hover:from-blue-50/30 hover:to-transparent transition-all duration-200 relative"
                    >
                      <div className="p-5 h-full flex flex-col space-y-4">
                        {/* Header with badge */}
                        <div className="flex items-start justify-between gap-2">
                          <h3 className="text-base font-semibold text-gray-900 leading-tight flex-1">{task.name}</h3>
                          {task.is_agentic !== null && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 flex-shrink-0">
                              {task.is_agentic ? "Agentic" : "Model"}
                            </span>
                          )}
                        </div>

                        {/* Metrics */}
                        <div className="flex gap-0 bg-gray-50 rounded-lg border border-gray-100 overflow-hidden">
                          <Tooltip title="Total traces recorded in the last 7 days" arrow placement="top">
                            <div className="flex-1 p-3 text-center border-r border-gray-200">
                              <TrendingUpIcon sx={{ fontSize: 20, color: "#3B82F6", mb: 0.5 }} />
                              <div className="text-xl font-semibold text-gray-900">{formatNumber(metrics.traceCount)}</div>
                              <div className="text-xs text-gray-500 mt-0.5">Traces</div>
                            </div>
                          </Tooltip>
                          <Tooltip title="Total tokens consumed in the last 7 days" arrow placement="top">
                            <div className="flex-1 p-3 text-center border-r border-gray-200">
                              <GeneratingTokensOutlinedIcon sx={{ fontSize: 20, color: "#A855F7", mb: 0.5 }} />
                              <div className="text-xl font-semibold text-gray-900">{formatNumber(metrics.totalTokens)}</div>
                              <div className="text-xs text-gray-500 mt-0.5">Tokens</div>
                            </div>
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
                            <div
                              className={`flex-1 p-3 text-center ${
                                metrics.successRate >= 1 && metrics.successRate < 50 ? "bg-red-50" : ""
                              }`}
                            >
                              {metrics.successRate >= 1 && metrics.successRate < 50 ? (
                                <ErrorOutlineIcon sx={{ fontSize: 20, color: "#EF4444", mb: 0.5 }} />
                              ) : (
                                <CheckCircleIcon sx={{ fontSize: 20, color: "#22C55E", mb: 0.5 }} />
                              )}
                              <div
                                className={`text-xl font-semibold ${
                                  metrics.successRate >= 1 && metrics.successRate < 50 ? "text-red-600" : "text-gray-900"
                                }`}
                              >
                                {metrics.successRate}%
                              </div>
                              <div
                                className={`text-xs mt-0.5 ${
                                  metrics.successRate >= 1 && metrics.successRate < 50 ? "text-red-600" : "text-gray-500"
                                }`}
                              >
                                Success
                              </div>
                            </div>
                          </Tooltip>
                        </div>

                      {/* Metadata */}
                      <div className="flex gap-8 text-xs">
                        <div className="flex flex-col gap-1">
                          <span className="text-gray-400">Last active</span>
                          <span className={`font-medium ${metrics.lastActive ? "text-gray-900" : "text-gray-400"}`}>
                            {formatLastActive(metrics.lastActive)}
                          </span>
                        </div>
                        <div className="flex flex-col gap-1">
                          <span className="text-gray-400">Created</span>
                          <span className="text-gray-900 font-medium">{new Date(task.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>

                        {/* Footer */}
                        <div className="flex items-center justify-between pt-3 border-t border-gray-100 mt-auto">
                          <span className="text-sm font-medium text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                            View traces →
                          </span>
                          <div className="relative">
                            {copiedTaskId === task.id ? (
                              <div
                                className="bg-green-50 border border-green-200 rounded-md px-3 py-1 flex items-center gap-1.5"
                                style={{ animation: "fadeIn 0.2s ease-in" }}
                              >
                                <CheckIcon sx={{ fontSize: 14, color: "#22C55E" }} />
                                <span className="text-xs text-green-700 font-medium">Copied!</span>
                              </div>
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
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </main>

        {/* Create Task Modal */}
        <CreateTaskForm
          open={showCreateForm}
          onTaskCreated={(taskId) => {
            setShowCreateForm(false);
            handleTaskCreated(taskId);
          }}
          onCancel={() => setShowCreateForm(false)}
        />
      </div>
    </>
  );
};
