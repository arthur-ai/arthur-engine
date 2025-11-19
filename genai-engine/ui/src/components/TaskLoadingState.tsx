'use client';

import React from 'react';

import { SidebarNavigation } from './SidebarNavigation';

interface TaskLoadingStateProps {
  onBackToDashboard: () => void;
  onLogout: () => void;
  onNavigate?: (sectionId: string) => void;
  activeSection?: string;
}

export const TaskLoadingState: React.FC<TaskLoadingStateProps> = ({
  onBackToDashboard,
  onLogout,
  onNavigate = () => {},
  activeSection = 'task-details'
}) => {
  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
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

      <div className="flex flex-1 overflow-hidden">
        <SidebarNavigation
          onBackToDashboard={onBackToDashboard}
          onNavigate={onNavigate}
          activeSection={activeSection}
        />

        <main className="flex-1 overflow-auto py-6 px-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        </main>
      </div>
    </div>
  );
};
