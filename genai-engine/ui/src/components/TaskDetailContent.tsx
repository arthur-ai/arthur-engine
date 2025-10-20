"use client";

import React from "react";

import { useTask } from "@/hooks/useTask";

export const TaskDetailContent: React.FC = () => {
  const { task } = useTask();

  if (!task) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  return (
    <div className="py-6 px-6">
      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">
              {task.name || "Untitled Task"}
            </h2>
            <div className="flex items-center space-x-2">
              {task.is_agentic && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  Agentic
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="px-6 py-4">
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-medium text-gray-500">Task ID</dt>
              <dd className="mt-1 text-sm text-gray-900 font-mono">
                {task.id}
              </dd>
            </div>

            {task.is_agentic !== undefined && (
              <div>
                <dt className="text-sm font-medium text-gray-500">Type</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {task.is_agentic ? "Agentic Task" : "Standard Task"}
                </dd>
              </div>
            )}

            <div>
              <dt className="text-sm font-medium text-gray-500">Created At</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {task.created_at
                  ? new Date(task.created_at).toLocaleString()
                  : "Not available"}
              </dd>
            </div>

            <div>
              <dt className="text-sm font-medium text-gray-500">Updated At</dt>
              <dd className="mt-1 text-sm text-gray-900">
                {task.updated_at
                  ? new Date(task.updated_at).toLocaleString()
                  : "Not available"}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  );
};
