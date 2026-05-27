import { describe, expect, it, vi } from "vitest";

import { TASK_TOUR_SKIP_WHEN } from "../content/wiring";
import { createTaskTourEmptyStatePredicate } from "../emptyState";

describe("createTaskTourEmptyStatePredicate", () => {
  it("checks evaluator emptiness with a one-row API query", async () => {
    const getAllLlmEvals = vi.fn().mockResolvedValue({
      data: { count: 0, llm_metadata: [] },
    });
    const isEmpty = createTaskTourEmptyStatePredicate(
      {
        api: {
          getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet: getAllLlmEvals,
        },
      } as never,
      "task-123"
    );

    await expect(isEmpty(TASK_TOUR_SKIP_WHEN.noEvaluators)).resolves.toBe(true);
    expect(getAllLlmEvals).toHaveBeenCalledWith({ taskId: "task-123", page: 0, page_size: 1 });
  });

  it("fails open for unknown keys, missing clients, existing evaluators, and request errors", async () => {
    const getAllLlmEvals = vi.fn().mockResolvedValue({
      data: { count: 2, llm_metadata: [{ name: "quality" }] },
    });
    const withClient = createTaskTourEmptyStatePredicate(
      {
        api: {
          getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet: getAllLlmEvals,
        },
      } as never,
      "task-123"
    );

    await expect(withClient("unknown")).resolves.toBe(false);
    expect(getAllLlmEvals).not.toHaveBeenCalled();

    await expect(createTaskTourEmptyStatePredicate(null, "task-123")(TASK_TOUR_SKIP_WHEN.noEvaluators)).resolves.toBe(false);
    await expect(withClient(TASK_TOUR_SKIP_WHEN.noEvaluators)).resolves.toBe(false);

    getAllLlmEvals.mockRejectedValueOnce(new Error("network"));
    await expect(withClient(TASK_TOUR_SKIP_WHEN.noEvaluators)).resolves.toBe(false);
  });

  it("falls back to metadata length and fails open for malformed evaluator responses", async () => {
    const getAllLlmEvals = vi
      .fn()
      .mockResolvedValueOnce({
        data: { llm_metadata: [] },
      })
      .mockResolvedValueOnce({
        data: {},
      });
    const isEmpty = createTaskTourEmptyStatePredicate(
      {
        api: {
          getAllLlmEvalsApiV1TasksTaskIdLlmEvalsGet: getAllLlmEvals,
        },
      } as never,
      "task-123"
    );

    await expect(isEmpty(TASK_TOUR_SKIP_WHEN.noEvaluators)).resolves.toBe(true);
    await expect(isEmpty(TASK_TOUR_SKIP_WHEN.noEvaluators)).resolves.toBe(false);
  });
});
