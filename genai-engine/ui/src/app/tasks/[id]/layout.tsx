"use client";

import {
  useParams,
  useRouter,
  useSelectedLayoutSegment,
  usePathname,
} from "next/navigation";
import { useState, useEffect } from "react";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/contexts/AuthContext";
import { TaskResponse } from "@/lib/api";
import { SidebarNavigation } from "@/components/SidebarNavigation";
import { TaskLoadingState } from "@/components/TaskLoadingState";
import { TaskErrorState } from "@/components/TaskErrorState";
import { TaskNotFoundState } from "@/components/TaskNotFoundState";
import { TaskProvider } from "@/contexts/TaskContext";

interface TaskLayoutProps {
  children: React.ReactNode;
}

export default function TaskLayout({ children }: TaskLayoutProps) {
  const params = useParams();
  const router = useRouter();
  const { logout } = useAuth();
  const api = useApi();
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const selectedLayoutSegment = useSelectedLayoutSegment();
  const pathname = usePathname();

  const taskId = params.id as string;
  // Map the current route to the active section
  // For playgrounds routes, we need to extract the full path segment
  let activeSection = selectedLayoutSegment || "task-details";

  // Handle playgrounds routes - extract the full path after the task ID
  if (pathname.includes("/playgrounds/")) {
    const pathSegments = pathname.split("/");
    const taskIndex = pathSegments.findIndex((segment) => segment === taskId);
    if (taskIndex !== -1 && pathSegments[taskIndex + 1] === "playgrounds") {
      activeSection = `playgrounds/${pathSegments[taskIndex + 2]}`;
    }
  }

  // Map section IDs to display titles
  const getPageTitle = (section: string): string => {
    const titleMap: Record<string, string> = {
      "task-details": "Task Details",
      traces: "Traces",
      retrievals: "Retrievals",
      evaluators: "Evaluators",
      datasets: "Datasets",
      "prompt-experiments": "Prompt Experiments",
      "rag-experiments": "RAG Experiments",
      "agent-experiments": "Agent Experiments",
      "playgrounds/prompts": "Prompts Playground",
      "playgrounds/retrievals": "Retrievals Playground",
    };
    return titleMap[section] || "Task Details";
  };

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

  const handleLogout = () => {
    logout();
  };

  const handleBack = () => {
    router.push("/");
  };

  if (loading) {
    return (
      <TaskLoadingState
        onBackToDashboard={handleBack}
        onLogout={handleLogout}
        onNavigate={(sectionId) => router.push(`/tasks/${taskId}/${sectionId}`)}
        activeSection={activeSection}
      />
    );
  }

  if (error) {
    return (
      <TaskErrorState
        error={error}
        onBackToDashboard={handleBack}
        onLogout={handleLogout}
        onNavigate={(sectionId) => router.push(`/tasks/${taskId}/${sectionId}`)}
        activeSection={activeSection}
      />
    );
  }

  if (!task) {
    return (
      <TaskNotFoundState
        onBackToDashboard={handleBack}
        onLogout={handleLogout}
        onNavigate={(sectionId) => router.push(`/tasks/${taskId}/${sectionId}`)}
        activeSection={activeSection}
      />
    );
  }

  return (
    <TaskProvider task={task}>
      <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="py-4">
              <h1 className="text-2xl font-semibold text-gray-900">
                {getPageTitle(activeSection)}
              </h1>
              <p className="text-gray-600">{task.name}</p>
            </div>
          </div>
        </header>

        <div className="flex flex-1">
          <SidebarNavigation
            onBackToDashboard={handleBack}
            onNavigate={(sectionId) => {
              // Navigate to the appropriate route
              router.push(`/tasks/${taskId}/${sectionId}`);
            }}
            onLogout={handleLogout}
            activeSection={activeSection}
          />

          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </div>
    </TaskProvider>
  );
}
