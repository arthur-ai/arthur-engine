'use client';

import { useParams, useRouter, useSelectedLayoutSegment } from 'next/navigation';
import { useState, useEffect } from 'react';
import { useApi } from '@/hooks/useApi';
import { useAuth } from '@/contexts/AuthContext';
import { TaskResponse } from '@/lib/api';
import { SidebarNavigation } from '@/components/SidebarNavigation';
import { TaskLoadingState } from '@/components/TaskLoadingState';
import { TaskErrorState } from '@/components/TaskErrorState';
import { TaskNotFoundState } from '@/components/TaskNotFoundState';
import { TaskProvider } from '@/contexts/TaskContext';

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

  const taskId = params.id as string;
  // Map the current route to the active section
  const activeSection = selectedLayoutSegment || 'task-details';

  // Map section IDs to display titles
  const getPageTitle = (section: string): string => {
    const titleMap: Record<string, string> = {
      'task-details': 'Task Details',
      'traces': 'Traces',
      'retrievals': 'Retrievals',
      'evaluators': 'Evaluators',
      'datasets': 'Datasets',
      'prompt-experiments': 'Prompt Experiments',
      'rag-experiments': 'RAG Experiments',
      'agent-experiments': 'Agent Experiments',
    };
    return titleMap[section] || 'Task Details';
  };

  useEffect(() => {
    const fetchTask = async () => {
      if (!api || !taskId) {
        setError('API client not available or task ID missing');
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
        console.error('Failed to fetch task:', err);
        setError('Failed to load task details');
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
    router.push('/');
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
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center py-4">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">
                  {getPageTitle(activeSection)}
                </h1>
                <p className="text-gray-600">{task.name}</p>
              </div>
              <button
                onClick={handleLogout}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
              >
                Logout
              </button>
            </div>
          </div>
        </header>

        <div className="flex">
          <SidebarNavigation 
            onBackToDashboard={handleBack}
            onNavigate={(sectionId) => {
              // Navigate to the appropriate route
              router.push(`/tasks/${taskId}/${sectionId}`);
            }}
            activeSection={activeSection}
          />

          <main className="flex-1">
            {children}
          </main>
        </div>
      </div>
    </TaskProvider>
  );
}
