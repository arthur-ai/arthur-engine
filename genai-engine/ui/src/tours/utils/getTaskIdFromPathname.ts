import { matchPath } from "react-router-dom";

const TASK_PATH_PATTERNS = ["/tasks/:taskId/*", "/tasks/:taskId"] as const;

export function getTaskIdFromPathname(pathname: string): string | undefined {
  for (const pattern of TASK_PATH_PATTERNS) {
    const match = matchPath({ path: pattern, end: false }, pathname);
    const taskId = match?.params.taskId;

    if (taskId && !taskId.startsWith(":")) {
      return taskId;
    }
  }

  return undefined;
}
