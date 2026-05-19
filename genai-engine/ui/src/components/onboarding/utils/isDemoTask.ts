import type { TaskResponse } from "@/lib/api-client/api-client";

// Temporary dev toggle: demo accounts are server-side scoped to a single task, so the
// tour is always on.
export const isDemoTask = (_task: TaskResponse | null | undefined): boolean => true;
