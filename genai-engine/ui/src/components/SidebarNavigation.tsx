'use client';

import React from 'react';

interface SidebarNavigationProps {
  onBackToDashboard: () => void;
  activeSection?: string;
}

export const SidebarNavigation: React.FC<SidebarNavigationProps> = ({
  onBackToDashboard,
  activeSection = 'task-details'
}) => {
  const navigationItems = [
    { id: 'all-tasks', label: '← All Tasks', onClick: onBackToDashboard },
    { id: 'task-details', label: 'Task Details' },
    { id: 'inferences', label: 'Inferences' },
    { id: 'metrics', label: 'Metrics' },
    { id: 'rules', label: 'Rules' },
    { id: 'settings', label: 'Settings' },
  ];

  return (
    <nav className="w-64 bg-white shadow-sm border-r border-gray-200 min-h-screen">
      <div className="p-4">
        <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">
          Navigation
        </h3>
        <ul className="space-y-2">
          {navigationItems.map((item) => {
            const isActive = item.id === activeSection;
            const isAllTasks = item.id === 'all-tasks';
            
            return (
              <li key={item.id}>
                <button
                  onClick={item.onClick}
                  className={`w-full text-left px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200 ${
                    isActive
                      ? 'text-blue-700 bg-blue-50'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  {item.label}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
};
