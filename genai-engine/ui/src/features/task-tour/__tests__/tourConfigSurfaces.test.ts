import { describe, expect, it } from "vitest";

import { TASK_TOUR_PREPARATIONS } from "../content/wiring";
import { TASK_TOUR_OCCLUDERS } from "../occluders";
import { buildTourConfig } from "../tour-config";

describe("task tour surfaces wiring", () => {
  it("keeps the trace drawer open exactly for the steps that open it", () => {
    const config = buildTourConfig("task-under-test");

    for (const section of config.sections) {
      for (const step of section.steps) {
        const opensDrawer = step.prepare?.key === TASK_TOUR_PREPARATIONS.traceOpened;
        const declaresDrawerOpen = (step.surfaces?.open ?? []).some((entry) => entry.id === TASK_TOUR_OCCLUDERS.traceDrawer);
        // Drawer-opening steps must keep the drawer open so reconcile doesn't
        // fight the prep hook; every other step must NOT (so a stranded drawer
        // is closed on entry).
        expect(declaresDrawerOpen, `${section.id}.${step.id}`).toBe(opensDrawer);
      }
    }
  });
});
