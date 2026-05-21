export type TourRuntimeStatus =
  | { status: "idle" }
  | { status: "navigating"; stepId: string; route: string }
  | { status: "waitingTarget"; stepId: string }
  | { status: "showing"; stepId: string; stepIndex: number }
  | { status: "waitingEvent"; stepId: string; eventName: string }
  | { status: "error"; stepId: string; reason: string }
  | { status: "completed"; tourId: string };

export type OrchestratorTickResult =
  | { action: "none" }
  | { action: "navigate"; route: string }
  | { action: "error"; reason: string };

export type TourAnalyticsPayload =
  | { type: "started"; tourId: string; stepId: string; sectionId: string }
  | { type: "step_viewed"; tourId: string; stepId: string; sectionId: string }
  | { type: "step_completed"; tourId: string; stepId: string; sectionId: string }
  | { type: "skipped"; tourId: string; stepId: string; sectionId: string; reason: string }
  | { type: "completed"; tourId: string }
  | { type: "error"; tourId: string; stepId: string; sectionId: string; errorReason: string };

export type TourOrchestratorCallbacks = {
  onStepChange: (stepId: string) => void;
  onTourComplete: (tourId: string) => void;
  onTourDismiss: (tourId: string) => void;
  onTourStop: () => void;
  onStatusChange: (status: TourRuntimeStatus) => void;
  onAnalytics: (payload: TourAnalyticsPayload) => void;
};
