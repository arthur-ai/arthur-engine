import AddIcon from "@mui/icons-material/Add";
import AppsOutlined from "@mui/icons-material/AppsOutlined";
import CloseIcon from "@mui/icons-material/Close";
import InventoryIcon from "@mui/icons-material/Inventory";
import KeyOutlined from "@mui/icons-material/KeyOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import SettingsIcon from "@mui/icons-material/Settings";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import SortIcon from "@mui/icons-material/Sort";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
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
import React, { useState, useEffect, useMemo, useCallback } from "react";
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
  const [archivedTasks, setArchivedTasks] = useState<TaskResponse[]>([]);
  const [isLoadingArchived, setIsLoadingArchived] = useState(false);
  const [archivedError, setArchivedError] = useState<string | null>(null);
  const [archivedLoaded, setArchivedLoaded] = useState(false);
  const [archivedDialogOpen, setArchivedDialogOpen] = useState(false);
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const isMenuOpen = Boolean(menuAnchorEl);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const { hideSystemTasks, sortBy, inactiveDays, setHideSystemTasks, setSortBy, setInactiveDays } = useTaskListStore();

  const filteredTasks = useMemo(() => {
    let result = [...tasks];

    if (hideSystemTasks) {
      result = result.filter((t) => !t.is_system_task);
    }

    if (inactiveDays !== "archived" && inactiveDays > 0) {
      const cutoff = Date.now() - inactiveDays * 24 * 60 * 60 * 1000;
      result = result.filter((t) => t.updated_at >= cutoff);
    }

    result.sort((a, b) => {
      const field = sortBy === "updated" ? "updated_at" : "created_at";
      return b[field] - a[field];
    });

    return result;
  }, [tasks, hideSystemTasks, sortBy, inactiveDays]);

  const filteredArchivedTasks = useMemo(() => {
    let result = [...archivedTasks];

    if (hideSystemTasks) {
      result = result.filter((t) => !t.is_system_task);
    }

    result.sort((a, b) => {
      const field = sortBy === "updated" ? "updated_at" : "created_at";
      return b[field] - a[field];
    });

    return result;
  }, [archivedTasks, hideSystemTasks, sortBy]);

  const fetchActiveTasks = useCallback(async () => {
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
  }, [api]);

  const fetchArchivedTasks = useCallback(async () => {
    try {
      setIsLoadingArchived(true);
      setArchivedError(null);

      if (!api) {
        throw new Error("API client not available");
      }

      const response = await api.api.searchTasksApiV2TasksSearchPost(
        {
          page_size: 50,
          page: 0,
        },
        {
          only_archived: true,
        }
      );

      setArchivedTasks(response.data.tasks || []);
      setArchivedLoaded(true);
    } catch (err) {
      console.error("Failed to fetch archived tasks:", err);
      setArchivedError("Failed to load archived tasks. Please check your authentication.");
    } finally {
      setIsLoadingArchived(false);
    }
  }, [api]);

  const handleArchiveToggle = useCallback(async () => {
    await fetchActiveTasks();
    if (archivedDialogOpen || archivedLoaded) {
      await fetchArchivedTasks();
    }
  }, [fetchActiveTasks, fetchArchivedTasks, archivedDialogOpen, archivedLoaded]);

  useEffect(() => {
    if (api) {
      fetchActiveTasks();
    }
  }, [api, fetchActiveTasks]);

  // Lazy-load archived tasks the first time the dialog is opened
  useEffect(() => {
    if (api && archivedDialogOpen && !archivedLoaded) {
      fetchArchivedTasks();
    }
  }, [api, archivedDialogOpen, archivedLoaded, fetchArchivedTasks]);

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
  };

  const handleTaskCreated = async (taskId: string) => {
    await fetchActiveTasks();
    navigate(`/tasks/${taskId}/overview`);
  };

  const filterToolbar = (
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
  );

  return (
    <>
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
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 256 }}>
                <CircularProgress />
              </Box>
            ) : error ? (
              <Alert severity="error">{error}</Alert>
            ) : tasks.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <Typography variant="h6" color="text.secondary">
                  No tasks found
                </Typography>
                <Typography variant="body2" color="text.disabled" sx={{ mb: 4 }}>
                  Get started by creating your first agent task.
                </Typography>
                <CreateTaskForm embedded={true} onTaskCreated={handleTaskCreated} onCancel={() => {}} />
              </Box>
            ) : (
              <>
                {/* Title + CTA */}
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2 }}>
                  <Box>
                    <Typography variant="h6">Tasks ({tasks.length})</Typography>
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

                {/* Filter toolbar */}
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
                  {filterToolbar}
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <ShowChartIcon sx={{ fontSize: 16, color: "text.disabled" }} />
                      <Typography variant="body2" color="text.secondary">
                        Metrics from last 7 days
                      </Typography>
                    </Stack>
                    <Tooltip title="View archived tasks">
                      <IconButton size="small" onClick={() => setArchivedDialogOpen(true)} sx={{ color: "text.disabled" }}>
                        <InventoryIcon sx={{ fontSize: 16 }} />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>

                {/* Active task grid */}
                {filteredTasks.length === 0 ? (
                  <Box sx={{ textAlign: "center", py: 6 }}>
                    <Typography variant="h6" color="text.secondary">
                      {inactiveDays === 0 ? "No tasks found" : `No tasks active in the last ${inactiveDays} days`}
                    </Typography>
                    {inactiveDays !== 0 && (
                      <Typography variant="body2" color="text.disabled">
                        Try expanding the time range or selecting &quot;All time&quot;.
                      </Typography>
                    )}
                  </Box>
                ) : (
                  <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" } }}>
                    {filteredTasks.map((task) => (
                      <TaskCard key={task.id} task={task} onArchiveToggle={handleArchiveToggle} />
                    ))}
                  </Box>
                )}
              </>
            )}
          </div>
        </main>

        {/* Archived Tasks Dialog */}
        <Dialog open={archivedDialogOpen} onClose={() => setArchivedDialogOpen(false)} maxWidth="lg" fullWidth>
          <DialogTitle sx={{ pb: 1 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <InventoryIcon sx={{ fontSize: 20, color: "text.secondary" }} />
                  <Typography variant="h6">Archived Tasks</Typography>
                  {!isLoadingArchived && archivedTasks.length > 0 && <Chip label={filteredArchivedTasks.length} size="small" variant="outlined" />}
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Unarchive a task to restore it to your active list
                </Typography>
              </Box>
              <IconButton onClick={() => setArchivedDialogOpen(false)} size="small" sx={{ mt: -0.5 }}>
                <CloseIcon />
              </IconButton>
            </Stack>
          </DialogTitle>
          <DialogContent dividers>
            {isLoadingArchived ? (
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: 200 }}>
                <CircularProgress />
              </Box>
            ) : archivedError ? (
              <Alert severity="error">{archivedError}</Alert>
            ) : filteredArchivedTasks.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 6 }}>
                <InventoryIcon sx={{ fontSize: 40, color: "text.disabled", mb: 1 }} />
                <Typography variant="h6" color="text.secondary">
                  No archived tasks
                </Typography>
                <Typography variant="body2" color="text.disabled">
                  Tasks you archive will appear here. Unarchive any task to restore it.
                </Typography>
              </Box>
            ) : (
              <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", lg: "repeat(3, 1fr)" }, pb: 1 }}>
                {filteredArchivedTasks.map((task) => (
                  <TaskCard key={task.id} task={task} onArchiveToggle={handleArchiveToggle} />
                ))}
              </Box>
            )}
          </DialogContent>
        </Dialog>

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
