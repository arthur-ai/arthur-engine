"use client";

import React from "react";

interface TaskErrorStateProps {
  error: string;
  onBackToDashboard: () => void;
}

export const TaskErrorState: React.FC<TaskErrorStateProps> = ({ error, onBackToDashboard }) => {
  return (
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
  );
};
