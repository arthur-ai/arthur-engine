import AddIcon from "@mui/icons-material/Add";
import MenuIcon from "@mui/icons-material/Menu";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import SortIcon from "@mui/icons-material/Sort";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import { Box, Button, FormControl, IconButton, MenuItem, Select, Stack, Tooltip, Typography } from "@mui/material";
import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { ArthurLogo } from "./common/ArthurLogo";
import { ThemeToggle } from "./common/ThemeToggle";
import { CreateTaskForm } from "./CreateTaskForm";
import { TaskCard } from "./TaskCard";

import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";
import { type InactiveDays, type SortBy, useTaskListStore } from "@/stores/task-list.store";

export const AllTasks: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const api = useApi();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const { hideSystemTasks, sortBy, inactiveDays, setHideSystemTasks, setSortBy, setInactiveDays } = useTaskListStore();

  const filteredTasks = useMemo(() => {
    let result = [...tasks];

    if (hideSystemTasks) {
      result = result.filter((t) => !t.is_system_task);
    }

    if (inactiveDays > 0) {
      const cutoff = Date.now() - inactiveDays * 24 * 60 * 60 * 1000;
      result = result.filter((t) => t.updated_at >= cutoff);
    }

    result.sort((a, b) => {
      const field = sortBy === "updated" ? "updated_at" : "created_at";
      return b[field] - a[field];
    });

    return result;
  }, [tasks, hideSystemTasks, sortBy, inactiveDays]);

  useEffect(() => {
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

        setTasks(response.data.tasks || []);
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
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        {/* Header */}
        <header className="bg-white dark:bg-gray-900 shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-3">
              <div className="flex flex-col items-start">
                <ArthurLogo className="h-20 -ml-5 text-black dark:text-white" />
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
                      bgcolor: "background.paper",
                      border: 1,
                      borderColor: "divider",
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
                    <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg py-2 z-50 border border-gray-200 dark:border-gray-700">
                      <div className="px-4 py-2">
                        <ThemeToggle />
                      </div>
                      <div className="border-t border-gray-200 dark:border-gray-700 mt-1 pt-1">
                        <Button variant="text" onClick={handleLogout} fullWidth sx={{ color: "text.primary" }}>
                          Logout
                        </Button>
                      </div>
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
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <div className="flex">
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800 dark:text-red-300">Error loading tasks</h3>
                    <div className="mt-2 text-sm text-red-700 dark:text-red-400">
                      <p>{error}</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : tasks.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-gray-500 dark:text-gray-400 text-lg font-medium mb-2">No tasks found</div>
                <p className="text-gray-400 dark:text-gray-500 mb-8">Get started by creating your first agent task.</p>
                <CreateTaskForm embedded={true} onTaskCreated={handleTaskCreated} onCancel={() => {}} />
              </div>
            ) : (
              <>
                <div className="mb-4">
                  <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">All Tasks ({tasks.length})</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                    {filteredTasks.length < tasks.length
                      ? `Showing ${filteredTasks.length} of ${tasks.length} tasks`
                      : "Click on any task to open the toolkit"}
                  </p>
                </div>

                {/* Filter & Sort Toolbar */}
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <SortIcon sx={{ fontSize: 18, color: "text.disabled" }} />
                      <FormControl size="small" variant="standard">
                        <Select
                          value={sortBy}
                          onChange={(e) => setSortBy(e.target.value as SortBy)}
                          disableUnderline
                          sx={{ fontSize: "0.875rem", color: "text.secondary" }}
                        >
                          <MenuItem value="updated">Recently updated</MenuItem>
                          <MenuItem value="created">Recently created</MenuItem>
                        </Select>
                      </FormControl>

                      <FormControl size="small" variant="standard">
                        <Select
                          value={inactiveDays}
                          onChange={(e) => setInactiveDays(e.target.value as InactiveDays)}
                          disableUnderline
                          sx={{ fontSize: "0.875rem", color: "text.secondary" }}
                        >
                          <MenuItem value={0}>All time</MenuItem>
                          <MenuItem value={7}>Active in last 7 days</MenuItem>
                          <MenuItem value={14}>Active in last 14 days</MenuItem>
                          <MenuItem value={30}>Active in last 30 days</MenuItem>
                        </Select>
                      </FormControl>
                    </Stack>

                    <Tooltip title={hideSystemTasks ? "Show system tasks" : "Hide system tasks"}>
                      <Stack
                        direction="row"
                        spacing={0.5}
                        alignItems="center"
                        onClick={() => setHideSystemTasks(!hideSystemTasks)}
                        sx={{ cursor: "pointer", "&:hover": { opacity: 0.7 } }}
                      >
                        {hideSystemTasks ? (
                          <VisibilityOffIcon sx={{ fontSize: 16, color: "text.disabled" }} />
                        ) : (
                          <VisibilityIcon sx={{ fontSize: 16, color: "text.disabled" }} />
                        )}
                        <Typography variant="body2" color="text.secondary">
                          {hideSystemTasks ? "System tasks hidden" : "System tasks visible"}
                        </Typography>
                      </Stack>
                    </Tooltip>
                  </Stack>

                  <Stack direction="row" spacing={0.5} alignItems="center">
                    <ShowChartIcon sx={{ fontSize: 16, color: "text.disabled" }} />
                    <Typography variant="body2" color="text.secondary">
                      Metrics from last 7 days
                    </Typography>
                  </Stack>
                </Box>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredTasks.map((task) => (
                    <TaskCard key={task.id} task={task} />
                  ))}
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
