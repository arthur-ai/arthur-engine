import type { DriveStep } from "driver.js";

import type { FlatTourStep } from "@/tours/registry";
import type { AnyTourEvents } from "@/tours/types";

export function mapStepToDriver<Events extends AnyTourEvents>(step: FlatTourStep<Events>): DriveStep {
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
  return steps.map(mapStepToDriver);
}
