export const toursEnabled = import.meta.env.VITE_ENABLE_TOURS === "true";

/** Fixed exercise task for the onboarding product tour (local / demo). */
export const onboardingExerciseTaskId =
  import.meta.env.VITE_ONBOARDING_EXERCISE_TASK_ID ?? "390a3d0c-65ae-4b9f-888b-a4a395875cf7";
