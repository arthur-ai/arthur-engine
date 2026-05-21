import mitt from "mitt";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { waitForElement } from "@/components/tour/utils/waitForElement";
import { onboardingTour } from "@/tours/onboarding/data";
import type { OnboardingTourEvents } from "@/tours/onboarding/events";

import { TourOrchestrator } from "./orchestrator";

vi.mock("@/components/tour/utils/waitForElement", () => ({
  waitForElement: vi.fn(),
}));

const drive = vi.fn();
const destroy = vi.fn();
const isActive = vi.fn(() => true);

vi.mock("driver.js", () => ({
  driver: vi.fn(() => ({
    drive,
    destroy,
    isActive,
  })),
}));

describe("TourOrchestrator", () => {
  const waitForElementMock = vi.mocked(waitForElement);

  beforeEach(() => {
    vi.clearAllMocks();
    waitForElementMock.mockResolvedValue(document.createElement("div"));
    isActive.mockReturnValue(true);
  });

  it("requests navigation when the current route does not match the step", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const onStepChange = vi.fn();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange,
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({})
    );

    orchestrator.start(onboardingTour, "welcome");
    const result = await orchestrator.tick("/settings");

    expect(result).toEqual({ action: "navigate", route: "/" });
    expect(onStepChange).toHaveBeenCalledWith("welcome");
  });

  it("drives the active step when the route and target are ready", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange: vi.fn(),
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({})
    );

    orchestrator.start(onboardingTour, "welcome");
    const result = await orchestrator.tick("/");

    expect(result).toEqual({ action: "none" });
    expect(drive).toHaveBeenCalledWith(0);
  });
});
