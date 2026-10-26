import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useTraceFeedback } from "./useTraceFeedback";

import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";
import type { TraceResponse } from "@/lib/api-client/api-client";
import { queryKeys } from "@/lib/queryKeys";

const api = vi.hoisted(() => ({
  annotateTraceApiV1TracesTraceIdAnnotationsPost: vi.fn(),
  deleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete: vi.fn(),
}));

vi.mock("@/hooks/useApi", () => ({ useApi: () => ({ api }) }));

vi.mock("notistack", () => ({ useSnackbar: () => ({ enqueueSnackbar: vi.fn() }) }));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: { feedbackAdded: "task-tour:feedback-added" },
}));

vi.mock("@/services/analytics", () => ({ track: vi.fn() }));

const TRACE_ID = "trace-id";

const trace = {
  trace_id: TRACE_ID,
  annotations: [
    { annotation_type: "human", annotation_score: 1 },
    { annotation_type: "continuous_eval", annotation_score: 0 },
  ],
} as TraceResponse;

const renderFeedback = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  queryClient.setQueryData(queryKeys.traces.byId(TRACE_ID), trace);
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  const { result } = renderHook(() => useTraceFeedback(TRACE_ID), { wrapper });
  const cachedAnnotationTypes = () =>
    queryClient.getQueryData<TraceResponse>(queryKeys.traces.byId(TRACE_ID))?.annotations?.map((a) => a.annotation_type);

  return { result, cachedAnnotationTypes };
};

describe("useTraceFeedback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not mark feedback complete when the feedback form is opened", () => {
    const { result } = renderFeedback();

    act(() => result.current.onOpen?.("positive"));

    expect(dispatchTourEvent).not.toHaveBeenCalled();
  });

  it("sends the rating and marks feedback added once the write succeeds", async () => {
    api.annotateTraceApiV1TracesTraceIdAnnotationsPost.mockResolvedValue({});
    const { result } = renderFeedback();

    await act(() => result.current.onSubmit({ score: 0, description: "Wrong tool" }));

    expect(api.annotateTraceApiV1TracesTraceIdAnnotationsPost).toHaveBeenCalledWith(TRACE_ID, {
      annotation_score: 0,
      annotation_description: "Wrong tool",
    });
    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.feedbackAdded);
  });

  it("rejects and restores the cached trace when the write fails", async () => {
    api.annotateTraceApiV1TracesTraceIdAnnotationsPost.mockRejectedValue(new Error("boom"));
    const { result, cachedAnnotationTypes } = renderFeedback();

    await expect(act(() => result.current.onSubmit({ score: 1, description: "" }))).rejects.toThrow("boom");

    expect(cachedAnnotationTypes()).toEqual(["human", "continuous_eval"]);
    expect(dispatchTourEvent).not.toHaveBeenCalled();
  });

  it("drops only the human rating from the cached trace while clearing", async () => {
    api.deleteAnnotationFromTraceApiV1TracesTraceIdAnnotationsDelete.mockReturnValue(new Promise(() => {}));
    const { result, cachedAnnotationTypes } = renderFeedback();

    act(() => void result.current.onClear());

    await waitFor(() => expect(cachedAnnotationTypes()).toEqual(["continuous_eval"]));
  });
});
