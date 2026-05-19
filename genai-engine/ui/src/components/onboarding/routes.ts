export const tourRoutes = {
  traces: (taskId: string) => `/tasks/${taskId}/traces`,
  datasets: (taskId: string) => `/tasks/${taskId}/datasets`,
  promptsManagement: (taskId: string) => `/tasks/${taskId}/prompts?tab=prompts-management`,
  promptsExperiments: (taskId: string) => `/tasks/${taskId}/prompts?tab=prompt-experiments`,
} as const;

export type TourRouteBuilder = (typeof tourRoutes)[keyof typeof tourRoutes];
