'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useApi } from '@/hooks/useApi';
import { useAuth } from '@/contexts/AuthContext';
import { TaskResponse } from '@/lib/api';
import { TaskLoadingState } from '@/components/TaskLoadingState';
import { TaskErrorState } from '@/components/TaskErrorState';
import { TaskNotFoundState } from '@/components/TaskNotFoundState';
import { TaskDetailContent } from '@/components/TaskDetailContent';

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { logout } = useAuth();
  const api = useApi();
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const taskId = params.id as string;

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
      />
    );
  }

  if (error) {
    return (
      <TaskErrorState 
        error={error}
        onBackToDashboard={handleBack}
        onLogout={handleLogout}
      />
    );
  }

  if (!task) {
    return (
      <TaskNotFoundState 
        onBackToDashboard={handleBack}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <TaskDetailContent 
      task={task}
      onBackToDashboard={handleBack}
      onLogout={handleLogout}
    />
  );
}
