import React, { useState, useEffect } from "react";
import { useParams, useNavigate, useLocation, Outlet } from "react-router-dom";

import { SidebarNavigation } from "@/components/SidebarNavigation";
import { TaskErrorState } from "@/components/TaskErrorState";
import { TaskLoadingState } from "@/components/TaskLoadingState";
import { TaskNotFoundState } from "@/components/TaskNotFoundState";
import { TaskProvider } from "@/contexts/TaskContext";
import { useApi } from "@/hooks/useApi";
import { TaskResponse } from "@/lib/api";

export const TaskLayout: React.FC = () => {
  const params = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const api = useApi();
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const taskId = params.id as string;

  // Map the current route to the active section
  let activeSection = "overview";

  // Extract the active section from the current path
  const pathSegments = location.pathname.split("/");
  const taskIndex = pathSegments.findIndex((segment) => segment === taskId);
  if (taskIndex !== -1 && pathSegments[taskIndex + 1]) {
    const section = pathSegments[taskIndex + 1];
    if (section === "playgrounds" && pathSegments[taskIndex + 2]) {
      activeSection = `playgrounds/${pathSegments[taskIndex + 2]}`;
    } else if (section === "prompts" && pathSegments[taskIndex + 2]) {
      // Map /tasks/:id/prompts/:promptName to prompts-management (legacy routes)
      activeSection = "prompts-management";
    } else if (section === "evaluators" || section === "continuous-evals") {
      // Map legacy evaluator/continuous-evals paths to the combined Evaluate nav item
      activeSection = "evaluate";
    } else if (section === "rag-notebooks" || section === "rag-experiments" || section === "rag-configurations") {
      // Legacy RAG sub-page routes highlight the unified "rag" sidebar item
      activeSection = "rag";
    } else {
      activeSection = section;
    }
  }

  useEffect(() => {
    const fetchTask = async () => {
      if (!api || !taskId) {
        setError("API client not available or task ID missing");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Use the direct get task by ID API endpoint
        const response = await api.api.getTaskApiV2TasksTaskIdGet(taskId);
        setTask(response.data);
      } catch (err) {
        console.error("Failed to fetch task:", err);
        setError("Failed to load task details");
      } finally {
        setLoading(false);
      }
    };

    fetchTask();
  }, [api, taskId]);

  const handleBack = () => {
    navigate("/");
  };

  const handleNavigate = (sectionId: string) => {
    navigate(`/tasks/${taskId}/${sectionId}`);
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-950 flex flex-col overflow-hidden">
      <div className="flex flex-1 overflow-hidden">
        <SidebarNavigation onBackToDashboard={handleBack} onNavigate={handleNavigate} activeSection={activeSection} taskName={task?.name} />

        <main className="flex-1 overflow-auto">
          {loading && (
            <div className="py-6 px-6">
              <TaskLoadingState />
            </div>
          )}
          {error && !loading && (
            <div className="py-6 px-6">
              <TaskErrorState error={error} onBackToDashboard={handleBack} />
            </div>
          )}
          {!task && !loading && !error && (
            <div className="py-6 px-6">
              <TaskNotFoundState onBackToDashboard={handleBack} />
            </div>
          )}
          {task && (
            <TaskProvider task={task}>
              <Outlet />
            </TaskProvider>
          )}
        </main>
      </div>
    </div>
  );
};
