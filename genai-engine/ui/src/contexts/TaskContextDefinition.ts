import { createContext } from "react";
import { TaskResponse } from "@/lib/api";

export interface TaskContextType {
  task: TaskResponse | null;
}

export const TaskContext = createContext<TaskContextType | undefined>(
  undefined
);
