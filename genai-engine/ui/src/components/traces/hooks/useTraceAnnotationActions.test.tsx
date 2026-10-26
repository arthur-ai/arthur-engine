import { AnnotationCell } from "@arthur/shared-components";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAnnotationCellOptions } from "./useTraceAnnotationActions";

import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";

vi.mock("@/hooks/useTask", () => ({ useTask: () => ({ task: { id: "task-id" } }) }));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: { annotationsReviewed: "task-tour:annotations-reviewed" },
}));

const annotation = {
  id: "annotation-id",
  annotation_type: "continuous_eval",
  annotation_score: 0,
  annotation_description: "Failed readability check",
  trace_id: "trace-id",
  continuous_eval_name: "Readability",
  eval_name: "Readability",
  run_status: "failed",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
} as const;

const TraceAnnotationCell = () => <AnnotationCell annotations={[annotation]} traceId="trace-id" {...useAnnotationCellOptions()} />;

describe("useAnnotationCellOptions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal(
      "ResizeObserver",
      class ResizeObserver {
        observe() {}
        unobserve() {}
        disconnect() {}
      }
    );
  });

  it("marks annotations reviewed only after the dialog is closed", () => {
    render(
      <MemoryRouter>
        <TraceAnnotationCell />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("button"));

    expect(dispatchTourEvent).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.annotationsReviewed);
  });
});
