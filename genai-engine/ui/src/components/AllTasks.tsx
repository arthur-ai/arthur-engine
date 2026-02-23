import AddIcon from "@mui/icons-material/Add";
import AppsOutlined from "@mui/icons-material/AppsOutlined";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import SortIcon from "@mui/icons-material/Sort";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  Box,
  Button,
  Divider,
  FormControl,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Select,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
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
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const isMenuOpen = Boolean(menuAnchorEl);
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

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

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
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <IconButton
                  aria-label="settings"
                  onClick={(e) => setMenuAnchorEl(e.currentTarget)}
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
                  <SettingsIcon />
                </IconButton>
                <Menu
                  anchorEl={menuAnchorEl}
                  open={isMenuOpen}
                  onClose={handleMenuClose}
                  anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                  transformOrigin={{ vertical: "top", horizontal: "right" }}
                >
                  <MenuItem
                    onClick={() => {
                      handleMenuClose();
                      navigate("/settings/model-providers");
                    }}
                  >
                    <ListItemIcon>
                      <AppsOutlined />
                    </ListItemIcon>
                    <ListItemText>Model Providers</ListItemText>
                  </MenuItem>
                  <MenuItem
                    onClick={() => {
                      handleMenuClose();
                      navigate("/settings/api-keys");
                    }}
                  >
                    <ListItemIcon>
                      <KeyOutlined />
                    </ListItemIcon>
                    <ListItemText>API Keys</ListItemText>
                  </MenuItem>
                  <Divider />
                  <Box sx={{ px: 2, py: 1 }}>
                    <ThemeToggle />
                  </Box>
                  <Divider />
                  <MenuItem onClick={handleLogout}>
                    <ListItemIcon>
                      <LogoutOutlined />
                    </ListItemIcon>
                    <ListItemText>Logout</ListItemText>
                  </MenuItem>
                </Menu>
              </Box>
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
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2 }}>
                  <Box>
                    <Typography variant="h6">All Tasks ({tasks.length})</Typography>
                    <Typography variant="body2" sx={{ color: "text.secondary", mt: 0.5 }}>
                      {filteredTasks.length < tasks.length
                        ? `Showing ${filteredTasks.length} of ${tasks.length} tasks`
                        : "Click on any task to open the toolkit"}
                    </Typography>
                  </Box>
                  <Button variant="contained" onClick={() => setShowCreateForm(true)} startIcon={<AddIcon />}>
                    Task
                  </Button>
                </Box>

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
