"use client";

import React from "react";

import { SidebarNavigation } from "./SidebarNavigation";

interface TaskErrorStateProps {
  error: string;
  onBackToDashboard: () => void;
  onLogout: () => void;
  onNavigate?: (sectionId: string) => void;
  activeSection?: string;
}

export const TaskErrorState: React.FC<TaskErrorStateProps> = ({
  error,
  onBackToDashboard,
  onLogout,
  onNavigate = () => {},
  activeSection = "task-details",
}) => {
  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-950 flex flex-col overflow-hidden">
      <header className="bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div>
              <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Task Details</h1>
            </div>
            <button
              onClick={onLogout}
              className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <SidebarNavigation onBackToDashboard={onBackToDashboard} onNavigate={onNavigate} activeSection={activeSection} />

        <main className="flex-1 overflow-auto py-6 px-6">
          <div className="bg-white dark:bg-gray-900 shadow rounded-lg p-6">
            <div className="text-center">
              <div className="text-red-600 dark:text-red-400 text-lg font-medium mb-2">Error Loading Task</div>
              <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
              <button
                onClick={onBackToDashboard}
                className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
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
