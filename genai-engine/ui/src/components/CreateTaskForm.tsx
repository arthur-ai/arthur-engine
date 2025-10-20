import React, { useState } from "react";

import { useApi } from "@/hooks/useApi";
import { NewTaskRequest } from "@/lib/api";

interface CreateTaskFormProps {
  onTaskCreated?: (taskId: string) => void;
  onCancel?: () => void;
}

export const CreateTaskForm: React.FC<CreateTaskFormProps> = ({
  onTaskCreated,
  onCancel,
}) => {
  const api = useApi();
  const [taskName, setTaskName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!taskName.trim()) {
      setError("Task name is required");
      return;
    }

    if (!api) {
      setError("API client not available");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);

      const taskData: NewTaskRequest = {
        name: taskName.trim(),
        is_agentic: true, // Always set to true as per requirements
      };

      const response = await api.api.createTaskApiV2TasksPost(taskData);

      // Call the callback with the new task ID
      if (onTaskCreated && response.data.id) {
        onTaskCreated(response.data.id);
      }

      // Reset form
      setTaskName("");
    } catch (err) {
      console.error("Failed to create task:", err);
      setError("Failed to create task. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setTaskName("");
    setError(null);
    if (onCancel) {
      onCancel();
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-w-md mx-auto">
      <h3 className="text-lg font-medium text-black mb-4">
        Create New Agent Task
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="taskName"
            className="block text-sm font-medium text-black mb-2"
          >
            Task Name
          </label>
          <input
            type="text"
            id="taskName"
            value={taskName}
            onChange={(e) => setTaskName(e.target.value)}
            placeholder="Enter task name..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-black"
            disabled={isSubmitting}
            autoFocus
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        <div className="flex space-x-3">
          {onCancel && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={isSubmitting}
              className="flex-1 bg-gray-300 text-black py-2 px-4 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              Cancel
            </button>
          )}

          <button
            type="submit"
            disabled={isSubmitting || !taskName.trim()}
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            {isSubmitting ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Creating...
              </div>
            ) : (
              "Create Task"
            )}
          </button>
        </div>
      </form>

      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-900">
          <span className="font-medium">Note:</span> This will create an agentic
          task that can be used for AI agent experiments and evaluations.
        </p>
      </div>
    </div>
  );
};
