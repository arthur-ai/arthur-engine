import { act, render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { createTourEngine } from "../../core/engine";
import { TourHost } from "../TourHost";
import { TourProvider } from "../TourProvider";
import { useRegisterQueryHook } from "../useRegisterQueryHook";

function CompositeTargetResolver() {
  useRegisterQueryHook("composite", () => document.querySelector("[data-surface]") ?? document.querySelector("[data-trigger]"));
  return null;
}

describe("ActiveTargetRefresh", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("refreshes active query-hook targets when a portalled surface mounts", async () => {
    const trigger = document.createElement("button");
    trigger.dataset.trigger = "true";
    document.body.appendChild(trigger);
    const found: Element[] = [];
    const engine = createTourEngine({
      config: {
        id: "tour",
        sections: [
          {
            id: "main",
            steps: [{ id: "composite", target: { kind: "queryHook", hookId: "composite" }, content: "Composite" }],
          },
        ],
      },
    });
    engine.on("target:found", (event) => found.push(event.element));

    render(
      <TourProvider tour={engine}>
        <TourHost>
          <CompositeTargetResolver />
        </TourHost>
      </TourProvider>
    );

    await act(async () => {
      await engine.start();
    });

    expect(found).toEqual([trigger]);

    const surface = document.createElement("section");
    surface.dataset.surface = "true";
    document.body.appendChild(surface);

    await waitFor(() => expect(found).toEqual([trigger, surface]));
  });

  it("re-resolves a selector target when its matching node is swapped", async () => {
    const stale = document.createElement("div");
    stale.dataset.target = "true";
    document.body.appendChild(stale);

    const found: Element[] = [];
    const engine = createTourEngine({
      config: {
        id: "tour",
        sections: [{ id: "main", steps: [{ id: "row", target: { kind: "selector", selector: "[data-target]" }, content: "Row" }] }],
      },
    });
    engine.on("target:found", (event) => found.push(event.element));

    render(
      <TourProvider tour={engine}>
        <TourHost>{null}</TourHost>
      </TourProvider>
    );

    await act(async () => {
      await engine.start();
    });

    expect(found).toEqual([stale]);

    // Mirror a route re-render replacing the node carrying the same id.
    stale.remove();
    const live = document.createElement("div");
    live.dataset.target = "true";
    document.body.appendChild(live);

    await waitFor(() => expect(found).toEqual([stale, live]));
  });

  it("clears a selector target (target:lost) when its node is removed", async () => {
    const node = document.createElement("div");
    node.dataset.target = "true";
    document.body.appendChild(node);

    let lost = 0;
    const engine = createTourEngine({
      config: {
        id: "tour",
        sections: [{ id: "main", steps: [{ id: "row", target: { kind: "selector", selector: "[data-target]" }, content: "Row" }] }],
      },
    });
    engine.on("target:lost", () => {
      lost += 1;
    });

    render(
      <TourProvider tour={engine}>
        <TourHost>{null}</TourHost>
      </TourProvider>
    );

    await act(async () => {
      await engine.start();
    });

    node.remove();
    // A second, unrelated mutation guarantees the observer fires after removal.
    document.body.appendChild(document.createElement("span"));

    await waitFor(() => expect(lost).toBeGreaterThan(0));
  });
});
