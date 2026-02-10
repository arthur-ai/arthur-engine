import AddIcon from "@mui/icons-material/Add";
import MenuIcon from "@mui/icons-material/Menu";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { CreateTaskForm } from "./CreateTaskForm";
import { TaskCard } from "./TaskCard";

import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";

export const AllTasks: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const api = useApi();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState<HTMLElement | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

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
                <>
                  <IconButton
                    aria-label="menu"
                    aria-haspopup="true"
                    aria-expanded={menuAnchorEl !== null ? "true" : undefined}
                    onClick={(e) => setMenuAnchorEl(e.currentTarget)}
                    sx={{
                      backgroundColor: "background.paper",
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: "4px",
                      padding: "8px",
                      width: "40px",
                      height: "40px",
                    }}
                  >
                    <MenuIcon />
                  </IconButton>
                  <Menu
                    anchorEl={menuAnchorEl}
                    open={menuAnchorEl !== null}
                    onClose={() => setMenuAnchorEl(null)}
                    anchorOrigin={{
                      vertical: "bottom",
                      horizontal: "right",
                    }}
                    transformOrigin={{
                      vertical: "top",
                      horizontal: "right",
                    }}
                    slotProps={{
                      paper: {
                        sx: {
                          width: "150px",
                        },
                      },
                    }}
                  >
                    <MenuItem
                      onClick={() => {
                        setMenuAnchorEl(null);
                      }}
                      sx={{
                        justifyContent: "end",
                      }}
                    >
                      User Settings
                    </MenuItem>
                    <MenuItem
                      onClick={() => {
                        setMenuAnchorEl(null);
                        handleLogout();
                      }}
                      sx={{
                        justifyContent: "end",
                      }}
                    >
                      Logout
                    </MenuItem>
                  </Menu>
                </>
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
                  {tasks.map((task) => (
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
