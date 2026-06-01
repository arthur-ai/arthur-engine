import { act, render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createTourEngine } from "../../core/engine";
import { TourHost } from "../TourHost";
import { TourProvider } from "../TourProvider";
import { useRegisterQueryHook } from "../useRegisterQueryHook";

function CompositeTargetResolver() {
  useRegisterQueryHook("composite", () => document.querySelector("[data-surface]") ?? document.querySelector("[data-trigger]"));
  return null;
}

describe("QueryHookTargetRefresh", () => {
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
});
