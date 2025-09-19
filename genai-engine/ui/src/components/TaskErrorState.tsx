'use client';

import React from 'react';
import { SidebarNavigation } from './SidebarNavigation';

interface TaskErrorStateProps {
  error: string;
  onBackToDashboard: () => void;
  onLogout: () => void;
}

export const TaskErrorState: React.FC<TaskErrorStateProps> = ({
  error,
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
          <div className="bg-white shadow rounded-lg p-6">
            <div className="text-center">
              <div className="text-red-600 text-lg font-medium mb-2">
                Error Loading Task
              </div>
              <p className="text-gray-600 mb-4">{error}</p>
              <button
                onClick={onBackToDashboard}
                className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
              >
                Back to Dashboard
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
