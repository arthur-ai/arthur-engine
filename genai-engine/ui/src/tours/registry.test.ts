import { describe, expect, it } from "vitest";

import { onboardingTour } from "./onboarding/data";
import { getFlatSteps, getStepIndexById } from "./registry";

describe("tour registry", () => {
  it("flattens sections with stable indices", () => {
    const steps = getFlatSteps(onboardingTour);

    expect(steps.length).toBeGreaterThanOrEqual(9);
    expect(steps[0]?.id).toBe("intro-adlc");
    expect(steps[0]?.type).toBe("modal");
    expect(steps[0]?.index).toBe(0);
    expect(steps.find((step) => step.id === "eval-modal")?.sectionId).toBe("evals");
  });

  it("resolves step index by id", () => {
    expect(getStepIndexById(onboardingTour, "send-message")).toBeGreaterThan(0);
    expect(getStepIndexById(onboardingTour, "missing")).toBe(-1);
  });
});
