'use client';

import React, { createContext, useContext, ReactNode } from 'react';
import { TaskResponse } from '@/lib/api';

interface TaskContextType {
  task: TaskResponse | null;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

interface TaskProviderProps {
  children: ReactNode;
  task: TaskResponse | null;
}

export const TaskProvider: React.FC<TaskProviderProps> = ({ children, task }) => {
  return (
    <TaskContext.Provider value={{ task }}>
      {children}
    </TaskContext.Provider>
  );
};

export const useTask = (): TaskContextType => {
  const context = useContext(TaskContext);
  if (context === undefined) {
    throw new Error('useTask must be used within a TaskProvider');
  }
  return context;
};
