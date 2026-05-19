import type { TaskResponse } from "@/lib/api-client/api-client";

// Dev/debug toggle for the onboarding tour. Demo accounts are scoped to a
// single task server-side and will always have the tour enabled, so this
// function exists only to flip the feature on/off during development and
// will be removed once the demo intro screen lands.
export const isDemoTask = (_task: TaskResponse | null | undefined): boolean => true;
