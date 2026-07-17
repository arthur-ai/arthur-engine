import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CreateTaskForm } from "./CreateTaskForm";

const trackMock = vi.hoisted(() => vi.fn());
const createTaskMock = vi.hoisted(() => vi.fn());

vi.mock("@/services/analytics", () => ({ track: trackMock }));
vi.mock("@/hooks/useApi", () => ({
  useApi: () => ({ api: { createTaskApiV2TasksPost: createTaskMock } }),
}));

describe("CreateTaskForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The failure path logs via console.error; silence to keep output clean.
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("emits task/created with the new task id on successful creation", async () => {
    createTaskMock.mockResolvedValue({ data: { id: "task-123" } });
    const onTaskCreated = vi.fn();

    render(<CreateTaskForm onTaskCreated={onTaskCreated} />);

    fireEvent.change(screen.getByPlaceholderText(/enter task name/i), { target: { value: "My Task" } });
    fireEvent.click(screen.getByRole("button", { name: /create task/i }));

    await waitFor(() => expect(onTaskCreated).toHaveBeenCalledWith("task-123"));

    expect(trackMock).toHaveBeenCalledWith("task/created", {
      task_id: "task-123",
      is_agentic: true,
      source: "create_task_form",
    });
  });

  it("does not emit task/created when creation fails", async () => {
    createTaskMock.mockRejectedValue(new Error("boom"));

    render(<CreateTaskForm />);

    fireEvent.change(screen.getByPlaceholderText(/enter task name/i), { target: { value: "My Task" } });
    fireEvent.click(screen.getByRole("button", { name: /create task/i }));

    await waitFor(() => expect(createTaskMock).toHaveBeenCalled());

    expect(trackMock).not.toHaveBeenCalled();
  });
});
