import { afterEach, describe, expect, it } from "vitest";

import { TOUR_IDS } from "../selectors";

import { isEvaluateResultsDetailsOpen } from "./EvaluateTargetWidget";

/**
 * The Annotation Details occluder's `isOpen()` is what lets `reconcileSurfaces`
 * dismiss the dialog when the tour enters a step (e.g. `traces / open-observe`)
 * whose target it covers. It keys off the dialog's own `data-tour-id` presence
 * (MUI unmounts a closed Dialog), so it can't break on a route rename or match
 * the trace drawer's same-named `?id`.
 */
describe("isEvaluateResultsDetailsOpen", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("is open when the details dialog is mounted (its data-tour-id is present)", () => {
    const dialog = document.createElement("div");
    dialog.setAttribute("data-tour-id", TOUR_IDS.evaluateResultsDetailsDialog);
    document.body.appendChild(dialog);
    expect(isEvaluateResultsDetailsOpen()).toBe(true);
  });

  it("is closed when the dialog is not rendered", () => {
    expect(isEvaluateResultsDetailsOpen()).toBe(false);
  });

  it("does not match an unrelated tour surface", () => {
    const other = document.createElement("div");
    other.setAttribute("data-tour-id", TOUR_IDS.traceAnnotationsModal);
    document.body.appendChild(other);
    expect(isEvaluateResultsDetailsOpen()).toBe(false);
  });
});
