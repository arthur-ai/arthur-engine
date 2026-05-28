import { beforeEach, describe, expect, it } from "vitest";

import { TOUR_IDS } from "../selectors";

import { resolveTraceActionsTarget, resolveTraceAddToDatasetActionTarget, resolveTraceAddToDatasetDrawerTarget } from "./TracesTargetWidget";

describe("trace Add-to-Dataset tour resolvers", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("resolves Trace Actions before guiding users to Add to Dataset", () => {
    document.body.innerHTML = `
      <section data-tour-id="${TOUR_IDS.traceDrawerAddToDataset}">Trace drawer</section>
      <nav data-tour-id="${TOUR_IDS.traceActions}">Trace Actions</nav>
      <button data-tour-id="${TOUR_IDS.traceAddToDatasetAction}">Add to Dataset</button>
      <aside data-tour-id="${TOUR_IDS.traceAddToDatasetDrawer}">Add-to-Dataset drawer</aside>
    `;

    expect(resolveTraceActionsTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.traceActions}"]`));
    expect(resolveTraceAddToDatasetActionTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.traceAddToDatasetAction}"]`));
    expect(resolveTraceAddToDatasetDrawerTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.traceAddToDatasetDrawer}"]`));
  });

  it("finds the Add-to-Dataset action by accessible text when shared components cannot accept a tour id", () => {
    document.body.innerHTML = `
      <section data-tour-id="${TOUR_IDS.traceDrawerAddToDataset}">
        <button>Add to Dataset</button>
      </section>
    `;

    expect(resolveTraceAddToDatasetActionTarget()).toBe(document.querySelector("button"));
  });
});
