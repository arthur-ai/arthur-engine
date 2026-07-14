import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const trackDynamicMock = vi.hoisted(() => vi.fn());
const trackMock = vi.hoisted(() => vi.fn());

vi.mock("@/services/analytics", () => ({ trackDynamic: trackDynamicMock, track: trackMock }));

// A truthy engine so TaskTour renders its provider subtree (the ErrorBoundary).
vi.mock("./useTaskTourEngine", () => ({
  useTaskTourEngine: () => ({ engine: { id: "engine" }, statePlugin: { getSnapshot: () => ({}) } }),
}));

vi.mock("@arthur/shared-components/tour/react-router", () => ({ useReactRouterNavigator: () => null }));
vi.mock("./chromeConfig", () => ({ useTaskTourChromeConfig: () => ({}) }));
vi.mock("./emptyState", () => ({ createTaskTourEmptyStatePredicate: () => () => false }));
vi.mock("./prep/useDetailRouteTourPrep", () => ({ useDetailRouteTourPrep: () => {} }));
vi.mock("./prep/useTracesTourPrep", () => ({ useTracesTourPrep: () => {} }));
vi.mock("./tourActions", () => ({
  registerTaskTourActionBridge: () => () => {},
  registerTaskTourTargetRefreshBridge: () => () => {},
}));
vi.mock("@/hooks/useApi", () => ({ useApi: () => ({}) }));
vi.mock("./widgets", () => ({
  CertificateWidget: () => null,
  DatasetTargetWidget: () => null,
  EvaluateTargetWidget: () => null,
  PromptTargetWidget: () => null,
  TaskTourFormPrefillWidget: () => null,
  TracesTargetWidget: () => null,
  TracesTourCleanupWidget: () => null,
}));

// TourSidePanel throws to simulate a render crash inside the tour surfaces.
vi.mock("@arthur/shared-components/tour", () => ({
  TourChromeProvider: ({ children }: { children: ReactNode }) => children,
  TourProvider: ({ children }: { children: ReactNode }) => children,
  TourHost: ({ children }: { children: ReactNode }) => children,
  TourSidePanel: () => {
    throw new Error("boom");
  },
  IntroWidget: () => null,
  SectionCompleteWidget: () => null,
  SpotlightWidget: () => null,
  GuidedStepPopover: () => null,
  OcclusionRecoveryWidget: () => null,
  ScrollTargetIntoViewWidget: () => null,
}));

import { TaskTour } from "./TaskTour";

describe("TaskTour render error boundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // React logs caught render errors; silence to keep the test output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("emits task-tour.render_error and stays mounted when a tour surface crashes", () => {
    expect(() => render(<TaskTour taskId="t1" />)).not.toThrow();

    expect(trackMock).toHaveBeenCalledWith("task-tour.render_error", expect.objectContaining({ message: "boom" }));
  });
});
