import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export type InactiveDays = 0 | 7 | 14 | 30 | "archived";

interface TaskListState {
  hideSystemTasks: boolean;
  inactiveDays: InactiveDays;
  setHideSystemTasks: (value: boolean) => void;
  setInactiveDays: (value: InactiveDays) => void;
}

export const useTaskListStore = create<TaskListState>()(
  devtools(
    persist(
      (set) => ({
        hideSystemTasks: true,
        inactiveDays: 0,
        setHideSystemTasks: (value) => set({ hideSystemTasks: value }, false, "taskList/setHideSystemTasks"),
        setInactiveDays: (value) => set({ inactiveDays: value }, false, "taskList/setInactiveDays"),
      }),
      { name: "arthur-task-list" }
    ),
    { name: "task-list-store" }
  )
);
