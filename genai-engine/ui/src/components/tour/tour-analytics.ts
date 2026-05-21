import type { TourAnalyticsPayload } from "@/components/tour/engine/types";
import { EVENT_NAMES, track } from "@/services/amplitude";

export function trackTourAnalytics(payload: TourAnalyticsPayload): void {
  switch (payload.type) {
    case "started":
      track(EVENT_NAMES.TOUR_STARTED, {
        tour_id: payload.tourId,
        step_id: payload.stepId,
        section_id: payload.sectionId,
      });
      break;
    case "step_viewed":
      track(EVENT_NAMES.TOUR_STEP_VIEWED, {
        tour_id: payload.tourId,
        step_id: payload.stepId,
        section_id: payload.sectionId,
      });
      break;
    case "step_completed":
      track(EVENT_NAMES.TOUR_STEP_COMPLETED, {
        tour_id: payload.tourId,
        step_id: payload.stepId,
        section_id: payload.sectionId,
      });
      break;
    case "skipped":
      track(EVENT_NAMES.TOUR_SKIPPED, {
        tour_id: payload.tourId,
        step_id: payload.stepId,
        section_id: payload.sectionId,
        reason: payload.reason,
      });
      break;
    case "completed":
      track(EVENT_NAMES.TOUR_COMPLETED, {
        tour_id: payload.tourId,
      });
      break;
    case "error":
      track(EVENT_NAMES.TOUR_ERROR, {
        tour_id: payload.tourId,
        step_id: payload.stepId,
        section_id: payload.sectionId,
        error_reason: payload.errorReason,
      });
      break;
  }
}
