import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createTourEngine } from "../../../core/engine";
import type { TourConfig } from "../../../core/types";
import { TourProvider } from "../../TourProvider";
import { GuidedStepPopover } from "../GuidedStepPopover";

class ResizeObserverStub {
  observe() {}
  disconnect() {}
}

function targetElement() {
  const element = document.createElement("button");
  element.getBoundingClientRect = () => new DOMRect(10, 10, 100, 40);
  // jsdom reports no client rects for every element; stub a box so the rect
  // pipeline treats it as rendered (useElementRect clears when length === 0).
  element.getClientRects = (() => [{} as DOMRect] as unknown as DOMRectList) as Element["getClientRects"];
  document.body.appendChild(element);
  return element;
}

function renderWithTour(config: TourConfig, children: ReactNode) {
  const engine = createTourEngine({ config });
  render(<TourProvider tour={engine}>{children}</TourProvider>);
  return engine;
}

describe("GuidedStepPopover", () => {
  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverStub);
    document.body.innerHTML = "";
  });

  it("does not render for default steps", async () => {
    const target = targetElement();
    const engine = renderWithTour(
      {
        id: "tour",
        sections: [{ id: "main", steps: [{ id: "default", target: { kind: "element", resolve: () => target }, content: "Default copy" }] }],
      },
      <GuidedStepPopover />
    );

    await act(async () => {
      await engine.start();
    });

    expect(screen.queryByText("Default copy")).toBeNull();
  });

  it("renders opted-in step content and advances from Next", async () => {
    const target = targetElement();
    const engine = renderWithTour(
      {
        id: "tour",
        sections: [
          {
            id: "main",
            steps: [
              {
                id: "guided",
                target: { kind: "element", resolve: () => target },
                content: "Review this area",
                popover: { showNext: true, nextLabel: "Got it" },
              },
              { id: "after", target: { kind: "element", resolve: () => target }, content: "After" },
            ],
          },
        ],
      },
      <GuidedStepPopover />
    );

    await act(async () => {
      await engine.start();
    });

    const next = await screen.findByRole("button", { name: /got it/i });
    expect(screen.getByText("Review this area")).not.toBeNull();

    fireEvent.click(next);

    await waitFor(() => expect(engine.getState()).toMatchObject({ status: "step", stepId: "after" }));
  });
});
