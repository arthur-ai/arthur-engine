import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

export type SortBy = "updated" | "created";
export type InactiveDays = 0 | 7 | 14 | 30 | "archived";

interface TaskListState {
  hideSystemTasks: boolean;
  sortBy: SortBy;
  inactiveDays: InactiveDays;
  setHideSystemTasks: (value: boolean) => void;
  setSortBy: (value: SortBy) => void;
  setInactiveDays: (value: InactiveDays) => void;
}

export const useTaskListStore = create<TaskListState>()(
  devtools(
    persist(
      (set) => ({
        hideSystemTasks: true,
        sortBy: "updated",
        inactiveDays: 0,
        setHideSystemTasks: (value) => set({ hideSystemTasks: value }, false, "taskList/setHideSystemTasks"),
        setSortBy: (value) => set({ sortBy: value }, false, "taskList/setSortBy"),
        setInactiveDays: (value) => set({ inactiveDays: value }, false, "taskList/setInactiveDays"),
      }),
      { name: "arthur-task-list" }
    ),
    { name: "task-list-store" }
  )
);
