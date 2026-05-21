import { onboardingTour } from "./onboarding/data";
import type { AnyTourEvents, Tour, TourStep } from "./types";

export const tours = {
  onboarding: onboardingTour,
} as const;

export type TourId = keyof typeof tours;

export type FlatTourStep<Events extends AnyTourEvents = AnyTourEvents> = TourStep<Events> & {
  sectionId: string;
  sectionTitle: string;
  index: number;
};

export function getActiveTour(tourId: TourId): Tour<AnyTourEvents>;
export function getActiveTour(tourId: string): Tour<AnyTourEvents> | null;
export function getActiveTour(tourId: string): Tour<AnyTourEvents> | null {
  if (tourId in tours) {
    return tours[tourId as TourId] as Tour<AnyTourEvents>;
  }
  return null;
}

export function getFlatSteps<Events extends AnyTourEvents = AnyTourEvents>(tour: Tour<Events>): FlatTourStep<Events>[] {
  let index = 0;
  return tour.sections.flatMap((section) =>
    section.steps.map((step) => ({
      ...step,
      sectionId: section.id,
      sectionTitle: section.title,
      index: index++,
    }))
  );
}

export function getStepIndexById<Events extends AnyTourEvents>(tour: Tour<Events>, stepId: string): number {
  return getFlatSteps(tour).findIndex((step) => step.id === stepId);
}
