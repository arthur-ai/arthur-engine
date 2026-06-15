import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { FeedbackPanel } from "./FeedbackPanel";

import { dispatchTourEvent } from "@/features/task-tour/tourEvents";

vi.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: vi.fn() }),
}));

vi.mock("@/hooks/useApi", () => ({
  useApi: () => ({
    api: {
      annotateTraceApiV1TracesTraceIdAnnotationsPost: vi.fn(),
      deleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete: vi.fn(),
    },
  }),
}));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    feedbackAdded: "task-tour:feedback-added",
  },
}));

vi.mock("@/services/analytics", () => ({
  track: vi.fn(),
}));

function renderFeedbackPanel() {
  const queryClient = new QueryClient();
  const container = document.createElement("div");
  document.body.appendChild(container);

  render(
    <QueryClientProvider client={queryClient}>
      <FeedbackPanel containerRef={{ current: container }} annotations={[]} traceId="trace-id" />
    </QueryClientProvider>
  );
}

describe("FeedbackPanel task tour events", () => {
  it("does not mark feedback complete when the feedback form is opened", () => {
    renderFeedbackPanel();

    fireEvent.click(screen.getByRole("button", { name: /helpful/i }));

    expect(dispatchTourEvent).not.toHaveBeenCalled();
  });
});
