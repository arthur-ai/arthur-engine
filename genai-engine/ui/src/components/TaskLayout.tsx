import React, { Suspense, lazy } from "react";
import { useParams, useNavigate, useLocation, Outlet } from "react-router-dom";

import { ChatbotDrawer } from "@/components/chatbot/ChatbotDrawer";
import { SidebarNavigation } from "@/components/SidebarNavigation";
import { TaskErrorState } from "@/components/TaskErrorState";
import { TaskLoadingState } from "@/components/TaskLoadingState";
import { TaskNotFoundState } from "@/components/TaskNotFoundState";
import { useAuth } from "@/contexts/AuthContext";
import { useDemoMode } from "@/contexts/EngineConfigContext";
import { TaskProvider } from "@/contexts/TaskContext";
import { useTaskQuery } from "@/hooks/tasks/useTaskQuery";

// The demo tour (engine + markdown content + sanitizer) only renders for demo
// tenants, so lazy-load it: non-demo users never download the chunk. The
// dynamic barrel import is the sanctioned mount point (the no-restricted-imports
// rule only guards static leaf-component imports).
const TaskTour = lazy(() => import("@/features/task-tour").then((m) => ({ default: m.TaskTour })));

export const TaskLayout: React.FC = () => {
  const params = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { demoMode } = useDemoMode();
  const { isTenant } = useAuth();
  // The guided demo tour is a demo-only experience: it should run only when the
  // engine is in demo mode AND the signed-in user is a demo tenant. Gating at the
  // mount point means the tour engine never initializes (and so never auto-starts)
  // for anyone else. `demoMode` defaults to false while engine-config loads, so the
  // tour stays off until both conditions are confirmed.
  const showTaskTour = demoMode && isTenant;

  const taskId = params.id as string;

  const { data, isPending, error: taskError } = useTaskQuery(taskId);
  const task = data ?? null;
  const loading = isPending;
  const error = taskError ? "Failed to load task details" : null;

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

  const handleBack = () => {
    navigate("/");
  };

  const handleNavigate = (sectionId: string) => {
    navigate(`/tasks/${taskId}/${sectionId}`);
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-950 flex flex-col overflow-hidden">
      {activeSection !== "chatbot" && <ChatbotDrawer taskId={taskId} />}
      <div className="flex flex-1 overflow-hidden">
        <SidebarNavigation onBackToDashboard={handleBack} onNavigate={handleNavigate} activeSection={activeSection} taskName={task?.name} />

        {task ? (
          // The page renders eagerly; when the demo tour is active the lazy
          // `TaskTour` sidecar mounts as a flex sibling of `<main>` (its docked
          // side panel takes window space from the app rather than floating over
          // it). Keeping the page outside the lazy boundary means it never waits
          // on — or remounts behind — the tour chunk.
          <TaskProvider task={task}>
            <main className="flex-1 overflow-auto">
              <Outlet />
            </main>
            {showTaskTour ? (
              <Suspense fallback={null}>
                <TaskTour taskId={task.id} />
              </Suspense>
            ) : null}
          </TaskProvider>
        ) : (
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
            {!loading && !error && (
              <div className="py-6 px-6">
                <TaskNotFoundState onBackToDashboard={handleBack} />
              </div>
            )}
          </main>
        )}
      </div>
    </div>
  );
};
