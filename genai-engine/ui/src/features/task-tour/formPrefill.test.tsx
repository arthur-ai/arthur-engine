import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useCallback, useState } from "react";
import { afterEach, describe, expect, it } from "vitest";

import {
  dispatchTaskTourFormPrefill,
  getTaskTourFormPrefillValue,
  shouldApplyTaskTourFormPrefill,
  useTaskTourFormPrefill,
  type TaskTourFormPrefill,
} from "./formPrefill";

afterEach(() => {
  cleanup();
});

function ComplexTourForm({ mode = "replace" }: { mode?: TaskTourFormPrefill["mode"] }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const handlePrefill = useCallback(
    (prefill: TaskTourFormPrefill) => {
      const hasExistingValue = Boolean(name.trim() || description.trim());
      if (!shouldApplyTaskTourFormPrefill(prefill, hasExistingValue)) return;
      const nextName = getTaskTourFormPrefillValue(prefill, "name");
      const nextDescription = getTaskTourFormPrefillValue(prefill, "description");
      if (typeof nextName === "string") setName(nextName);
      if (typeof nextDescription === "string") setDescription(nextDescription);
    },
    [description, name]
  );

  useTaskTourFormPrefill("task-tour-complex-form", handlePrefill);

  return (
    <>
      <input aria-label="Name" value={name} onChange={(event) => setName(event.target.value)} />
      <input aria-label="Description" value={description} onChange={(event) => setDescription(event.target.value)} />
      <button
        type="button"
        onClick={() =>
          dispatchTaskTourFormPrefill({
            targetId: "task-tour-complex-form",
            mode,
            values: {
              name: "Demo experiment",
              description: "Compare prompt variants",
            },
          })
        }
      >
        Prefill
      </button>
    </>
  );
}

describe("task tour form prefill", () => {
  it("lets complex forms consume named prefill values", () => {
    render(<ComplexTourForm />);

    fireEvent.click(screen.getByRole("button", { name: /prefill/i }));

    expect((screen.getByLabelText("Name") as HTMLInputElement).value).toBe("Demo experiment");
    expect((screen.getByLabelText("Description") as HTMLInputElement).value).toBe("Compare prompt variants");
  });

  it("lets complex forms preserve existing values in empty-only mode", () => {
    render(<ComplexTourForm mode="empty-only" />);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "User name" } });

    fireEvent.click(screen.getByRole("button", { name: /prefill/i }));

    expect((screen.getByLabelText("Name") as HTMLInputElement).value).toBe("User name");
    expect((screen.getByLabelText("Description") as HTMLInputElement).value).toBe("");
  });

  it("dispatches values maps through the shared event", () => {
    const received: TaskTourFormPrefill[] = [];
    const listener = (event: Event) => received.push((event as CustomEvent<TaskTourFormPrefill>).detail);
    window.addEventListener("task-tour:form-prefill", listener);

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: "task-tour-complex-form",
        values: { name: "Demo experiment" },
      });
    });

    expect(received).toEqual([{ targetId: "task-tour-complex-form", values: { name: "Demo experiment" } }]);
    window.removeEventListener("task-tour:form-prefill", listener);
  });
});
