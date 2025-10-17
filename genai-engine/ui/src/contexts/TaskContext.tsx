import React, { ReactNode } from "react";

import { TaskContext, TaskContextType } from "./TaskContextDefinition";

interface TaskProviderProps {
  children: ReactNode;
  task: TaskContextType["task"];
}

export const TaskProvider: React.FC<TaskProviderProps> = ({
  children,
  task,
}) => {
  return (
    <TaskContext.Provider value={{ task }}>{children}</TaskContext.Provider>
  );
};
