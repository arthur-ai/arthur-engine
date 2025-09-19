'use client';

import React from 'react';
import { SidebarNavigation } from './SidebarNavigation';
import { TaskResponse } from '@/lib/api';

interface TaskDetailContentProps {
  task: TaskResponse;
  onBackToDashboard: () => void;
  onLogout: () => void;
}

export const TaskDetailContent: React.FC<TaskDetailContentProps> = ({
  task,
  onBackToDashboard,
  onLogout
}) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900">
                Task Details
              </h1>
              <p className="text-gray-600">Task ID: {task.id}</p>
            </div>
            <button
              onClick={onLogout}
              className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        <SidebarNavigation 
          onBackToDashboard={onBackToDashboard}
          activeSection="task-details"
        />

        <main className="flex-1 py-6 px-6">
          <div className="bg-white shadow rounded-lg">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium text-gray-900">
                  {task.name || 'Untitled Task'}
                </h2>
                <div className="flex items-center space-x-2">
                  {task.is_agentic && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Agentic
                    </span>
                  )}
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    {task.status || 'Unknown'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4">
              <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Task ID</dt>
                  <dd className="mt-1 text-sm text-gray-900 font-mono">{task.id}</dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1 text-sm text-gray-900">{task.status || 'Not specified'}</dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created At</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {task.created_at ? new Date(task.created_at).toLocaleString() : 'Not available'}
                  </dd>
                </div>
                
                <div>
                  <dt className="text-sm font-medium text-gray-500">Updated At</dt>
                  <dd className="mt-1 text-sm text-gray-900">
                    {task.updated_at ? new Date(task.updated_at).toLocaleString() : 'Not available'}
                  </dd>
                </div>
                
                {task.is_agentic !== undefined && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Type</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      {task.is_agentic ? 'Agentic Task' : 'Standard Task'}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
