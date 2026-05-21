import type { DriveStep } from "driver.js";

import type { FlatTourStep } from "@/tours/registry";
import type { AnyTourEvents, TourStep } from "@/tours/types";

type DriverMappedTourStep<Events extends AnyTourEvents> = Extract<TourStep<Events>, { type: "popover" } | { type: "task" }>;

export function mapStepToDriver<Events extends AnyTourEvents>(step: DriverMappedTourStep<Events>): DriveStep {
  const isTaskStep = step.type === "task";

  return {
    element: step.selector,
    popover: {
      title: step.title,
      description: step.description,
      showProgress: true,
      popoverClass: "arthur-tour-popover",
      showButtons: isTaskStep ? ["close"] : ["next", "previous", "close"],
      disableButtons: isTaskStep ? ["next", "previous"] : undefined,
    },
  };
}

export function mapTourStepsToDriver<Events extends AnyTourEvents>(steps: FlatTourStep<Events>[]): DriveStep[] {
  return steps.filter((step): step is FlatTourStep<Events> & DriverMappedTourStep<Events> => step.type !== "modal").map(mapStepToDriver);
}

export function getDriverIndexForFlatStep<Events extends AnyTourEvents>(steps: FlatTourStep<Events>[], flatIndex: number): number {
  const nonModalStepsBefore = steps.slice(0, flatIndex + 1).filter((step) => step.type !== "modal");
  return nonModalStepsBefore.length - 1;
}
