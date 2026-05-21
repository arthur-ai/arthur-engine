import { describe, expect, it } from "vitest";

import { onboardingTour } from "./onboarding/data";
import { getFlatSteps, getStepIndexById } from "./registry";

describe("tour registry", () => {
  it("flattens sections with stable indices", () => {
    const steps = getFlatSteps(onboardingTour);

    expect(steps).toHaveLength(2);
    expect(steps[0]?.id).toBe("welcome");
    expect(steps[0]?.index).toBe(0);
    expect(steps[1]?.id).toBe("settings");
    expect(steps[1]?.index).toBe(1);
    expect(steps[1]?.sectionId).toBe("settings");
  });

  it("resolves step index by id", () => {
    expect(getStepIndexById(onboardingTour, "settings")).toBe(1);
    expect(getStepIndexById(onboardingTour, "missing")).toBe(-1);
  });
});
