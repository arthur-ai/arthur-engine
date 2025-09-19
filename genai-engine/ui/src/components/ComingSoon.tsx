'use client';

import React from 'react';

interface ComingSoonProps {
  featureName: string;
  description?: string;
}

export const ComingSoon: React.FC<ComingSoonProps> = ({
  featureName,
  description
}) => {
  return (
    <div className="h-full bg-gray-50 flex items-center justify-center p-6">
      <div className="max-w-md mx-auto text-center">
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="mb-6">
            <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 mb-4">
              <svg
                className="h-8 w-8 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">
              Coming Soon
            </h1>
            <h2 className="text-lg font-medium text-gray-700 mb-4">
              {featureName}
            </h2>
            {description && (
              <p className="text-gray-600 mb-6">
                {description}
              </p>
            )}
            <p className="text-sm text-gray-500">
              This feature is currently under development and will be available soon.
            </p>
          </div>
          
          <div className="border-t border-gray-200 pt-6">
            <div className="flex items-center justify-center space-x-2 text-sm text-gray-500">
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 10V3L4 14h7v7l9-11h-7z"
                />
              </svg>
              <span>Stay tuned for updates!</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
