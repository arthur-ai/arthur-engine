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

  it("spotlights the Trace Actions trigger while the Add-to-Dataset menu item is hidden, then snaps to the item when opened", () => {
    // Mirrors the shared-components Base UI Menu: the trigger is always
    // visible, while the `keepMounted` popup (and its menu items) is `hidden`
    // until the user opens it.
    document.body.innerHTML = `
      <section data-tour-id="${TOUR_IDS.traceDrawerAddToDataset}">
        <button>Trace Actions</button>
        <div hidden data-menu-popup>
          <div role="menuitem">Refresh Metrics</div>
          <div role="menuitem">Add to Dataset Add this trace to a dataset</div>
        </div>
      </section>
    `;

    const trigger = document.querySelector("button");
    const menuItem = Array.from(document.querySelectorAll('[role="menuitem"]')).find((el) => /add to dataset/i.test(el.textContent ?? ""));

    // Closed menu: the item is hidden, so the spotlight sits on the trigger.
    expect(resolveTraceActionsTarget()).toBe(trigger);
    expect(resolveTraceAddToDatasetActionTarget()).toBe(trigger);

    // Open the menu: the resolver now snaps to the visible Add-to-Dataset item.
    document.querySelector("[data-menu-popup]")!.removeAttribute("hidden");
    expect(resolveTraceAddToDatasetActionTarget()).toBe(menuItem);
  });
});
