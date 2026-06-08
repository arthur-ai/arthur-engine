import { act, render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TASK_TOUR_FORM_PREFILL_EVENT, type TaskTourFormPrefill } from "../formPrefill";

import { TaskTourFormPrefillWidget } from "./TaskTourFormPrefillWidget";

import { createTourEngine, TourProvider } from "@/features/tour";

describe("TaskTourFormPrefillWidget", () => {
  it("emits the active step form prefill when the step enters", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const received: TaskTourFormPrefill[] = [];
    const listener = (event: Event) => {
      received.push((event as CustomEvent<TaskTourFormPrefill>).detail);
    };
    window.addEventListener(TASK_TOUR_FORM_PREFILL_EVENT, listener);

    const engine = createTourEngine({
      config: {
        id: "tour",
        sections: [
          {
            id: "agent",
            steps: [
              {
                id: "send-message",
                target: { kind: "element", resolve: () => target },
                content: "Send a message",
                formPrefill: {
                  targetId: "task-tour-chat-send",
                  value: "What is an AI Agent?",
                },
              },
            ],
          },
        ],
      },
    });

    render(
      <TourProvider tour={engine}>
        <TaskTourFormPrefillWidget />
      </TourProvider>
    );

    await act(async () => {
      await engine.start();
    });

    expect(received).toEqual([
      {
        targetId: "task-tour-chat-send",
        value: "What is an AI Agent?",
      },
    ]);

    window.removeEventListener(TASK_TOUR_FORM_PREFILL_EVENT, listener);
    target.remove();
  });

  it("re-emits form prefill when the active target refreshes onto the form target", async () => {
    const trigger = document.createElement("button");
    const modal = document.createElement("div");
    modal.setAttribute("data-tour-id", "task-tour-synthetic-modal");
    document.body.append(trigger, modal);
    let activeTarget: Element = trigger;
    const received: TaskTourFormPrefill[] = [];
    const listener = (event: Event) => {
      received.push((event as CustomEvent<TaskTourFormPrefill>).detail);
    };
    window.addEventListener(TASK_TOUR_FORM_PREFILL_EVENT, listener);

    const engine = createTourEngine({
      config: {
        id: "tour",
        sections: [
          {
            id: "datasets",
            steps: [
              {
                id: "generate-synthetic",
                target: { kind: "element", resolve: () => activeTarget },
                content: "Generate synthetic data",
                formPrefill: {
                  targetId: "task-tour-synthetic-modal",
                  values: { datasetPurpose: "Data for testing general-purpose wikipedia search agent" },
                  mode: "empty-only",
                },
              },
            ],
          },
        ],
      },
    });

    render(
      <TourProvider tour={engine}>
        <TaskTourFormPrefillWidget />
      </TourProvider>
    );

    await act(async () => {
      await engine.start();
    });
    received.length = 0;

    act(() => {
      activeTarget = modal;
      engine.refreshTarget();
    });

    expect(received).toEqual([
      {
        targetId: "task-tour-synthetic-modal",
        values: { datasetPurpose: "Data for testing general-purpose wikipedia search agent" },
        mode: "empty-only",
      },
    ]);

    window.removeEventListener(TASK_TOUR_FORM_PREFILL_EVENT, listener);
    trigger.remove();
    modal.remove();
  });
});
