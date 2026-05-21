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

  it("does not navigate when route params are missing", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange: vi.fn(),
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onMinimizeGuidance: vi.fn(),
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({}),
      () => true
    );

    orchestrator.start(onboardingTour, "intro-adlc");
    const result = await orchestrator.tick("/");

    expect(result).toEqual({ action: "none" });
  });

  it("requests navigation to the resolved task route", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const onStepChange = vi.fn();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange,
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onMinimizeGuidance: vi.fn(),
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({ taskId: "task-abc" }),
      () => true
    );

    orchestrator.start(onboardingTour, "intro-adlc");
    const result = await orchestrator.tick("/");

    expect(result).toEqual({ action: "navigate", route: "/tasks/task-abc/overview" });
    expect(onStepChange).toHaveBeenCalledWith("intro-adlc");
  });

  it("shows modal step when already on the resolved task route", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange: vi.fn(),
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onMinimizeGuidance: vi.fn(),
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({ taskId: "task-abc" }),
      () => true
    );

    orchestrator.start(onboardingTour, "intro-adlc");
    const result = await orchestrator.tick("/tasks/task-abc/overview");

    expect(result).toEqual({ action: "none" });
    expect(drive).not.toHaveBeenCalled();
  });

  it("hides driver and waits for events on task steps", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange: vi.fn(),
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onMinimizeGuidance: vi.fn(),
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({ taskId: "task-abc" }),
      () => true
    );

    orchestrator.start(onboardingTour, "chatbot-opened");
    const result = await orchestrator.tick("/tasks/task-abc/overview");

    expect(result).toEqual({ action: "none" });
    expect(drive).not.toHaveBeenCalled();
    expect(destroy).toHaveBeenCalled();
    expect(orchestrator.getStatus()).toEqual({
      status: "waitingEvent",
      stepId: "chatbot-opened",
      eventName: "onboarding:chatbot-opened",
    });
  });

  it("skips driver popover when guidance is minimized", async () => {
    const emitter = mitt<OnboardingTourEvents>();
    const onMinimizeGuidance = vi.fn();
    const orchestrator = new TourOrchestrator(
      emitter,
      {
        onStepChange: vi.fn(),
        onTourComplete: vi.fn(),
        onTourDismiss: vi.fn(),
        onTourStop: vi.fn(),
        onMinimizeGuidance,
        onStatusChange: vi.fn(),
        onAnalytics: vi.fn(),
      },
      () => ({ taskId: "task-abc" }),
      () => false
    );

    orchestrator.start(onboardingTour, "exercise-context");
    const result = await orchestrator.tick("/tasks/task-abc/overview");

    expect(result).toEqual({ action: "none" });
    expect(drive).not.toHaveBeenCalled();
    expect(orchestrator.getStatus()).toEqual({ status: "minimized", stepId: "exercise-context" });
  });
});
