import { findMajorTaskForStep, type MajorTaskId, STEPS, type StepId } from "./steps";

import { EVENT_NAMES, track } from "@/services/amplitude";

export type OnboardingSource =
  | "next_button"
  | "user_action"
  | "auto_advance"
  | "checklist_replay"
  | "skip_section_button"
  | "tooltip_close"
  | "widget_close"
  | "skip_to_end"
  | "unknown";

export interface OnboardingSnapshot {
  step_index: number;
  completed_count: number;
  skipped_count: number;
}

interface CommonProps {
  step_id: StepId | null;
  step_index: number;
  major_task_id: MajorTaskId | null;
  major_task_label: string | null;
  total_steps: number;
  completed_count: number;
  skipped_count: number;
}

const buildCommonProps = (snapshot: OnboardingSnapshot): CommonProps => {
  const step = STEPS[snapshot.step_index];
  const majorTask = step ? findMajorTaskForStep(step.id) : undefined;
  return {
    step_id: step?.id ?? null,
    step_index: snapshot.step_index,
    major_task_id: majorTask?.id ?? null,
    major_task_label: majorTask?.label ?? null,
    total_steps: STEPS.length,
    completed_count: snapshot.completed_count,
    skipped_count: snapshot.skipped_count,
  };
};

export const trackOnboardingStarted = (snapshot: OnboardingSnapshot, isResume: boolean): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_STARTED, {
    ...buildCommonProps(snapshot),
    is_resume: isResume,
  });
};

export const trackStepViewed = (snapshot: OnboardingSnapshot): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_STEP_VIEWED, { ...buildCommonProps(snapshot) });
};

export const trackStepCompleted = (snapshot: OnboardingSnapshot, source: OnboardingSource): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_STEP_COMPLETED, {
    ...buildCommonProps(snapshot),
    source,
  });
};

export const trackStepSkipped = (snapshot: OnboardingSnapshot, source: OnboardingSource, skippedStepIds: StepId[]): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_STEP_SKIPPED, {
    ...buildCommonProps(snapshot),
    source,
    skipped_step_ids: skippedStepIds,
  });
};

export const trackMajorTaskCompleted = (snapshot: OnboardingSnapshot): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_MAJOR_TASK_COMPLETED, { ...buildCommonProps(snapshot) });
};

export const trackMajorTaskSkipped = (snapshot: OnboardingSnapshot, subtasksSkipped: StepId[]): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_MAJOR_TASK_SKIPPED, {
    ...buildCommonProps(snapshot),
    subtasks_skipped: subtasksSkipped,
  });
};

export const trackOnboardingCompleted = (snapshot: OnboardingSnapshot): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_COMPLETED, { ...buildCommonProps(snapshot) });
};

export const trackOnboardingDismissed = (snapshot: OnboardingSnapshot, source: OnboardingSource): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_DISMISSED, {
    ...buildCommonProps(snapshot),
    source,
  });
};

export const trackOnboardingReplayed = (snapshot: OnboardingSnapshot, fromStatus: "completed" | "dismissed"): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_REPLAYED, {
    ...buildCommonProps(snapshot),
    from_status: fromStatus,
  });
};

export const trackOnboardingReset = (snapshot: OnboardingSnapshot): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_RESET, { ...buildCommonProps(snapshot) });
};

export const trackPanelToggled = (snapshot: OnboardingSnapshot, collapsed: boolean): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_PANEL_TOGGLED, {
    ...buildCommonProps(snapshot),
    collapsed,
  });
};

export const trackChecklistSubtaskClicked = (
  snapshot: OnboardingSnapshot,
  targetStepId: StepId,
  targetMajorTaskId: MajorTaskId,
  isJumpAcrossTasks: boolean
): void => {
  track(EVENT_NAMES.ONBOARDING_TOUR_CHECKLIST_SUBTASK_CLICKED, {
    ...buildCommonProps(snapshot),
    target_step_id: targetStepId,
    target_major_task_id: targetMajorTaskId,
    is_jump_across_tasks: isJumpAcrossTasks,
  });
};
