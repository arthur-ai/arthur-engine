import AddIcon from "@mui/icons-material/Add";
import MenuIcon from "@mui/icons-material/Menu";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";

import { CreateTaskForm } from "./CreateTaskForm";
import { TaskCard } from "./TaskCard";

export const AllTasks: React.FC = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const api = useApi();
  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
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
