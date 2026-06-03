import { describe, expect, it } from "vitest";

import { TASK_TOUR_WIRING } from "../content/wiring";
import { TASK_TOUR_TARGET_LOST_HINTS } from "../tourActions";

// The hint map is keyed by free `${sectionId}.${stepId}` strings with no type
// linkage to the wiring, so a step rename can silently orphan a hint (the
// `?? null` lookup swallows misses). Guard the keys against the wiring here.
describe("TASK_TOUR_TARGET_LOST_HINTS", () => {
  it("keys every hint to a real ${sectionId}.${stepId} in the wiring", () => {
    for (const key of Object.keys(TASK_TOUR_TARGET_LOST_HINTS)) {
      const dot = key.indexOf(".");
      const sectionId = key.slice(0, dot);
      const stepId = key.slice(dot + 1);
      const section = TASK_TOUR_WIRING[sectionId];
      expect(section, `hint key "${key}" references unknown section "${sectionId}"`).toBeTruthy();
      expect(section.steps[stepId], `hint key "${key}" references unknown step "${stepId}"`).toBeTruthy();
    }
  });
});
