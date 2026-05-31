import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { getPulseExpansionGeometry, PulsingRing } from "./PulsingRing";

describe("PulsingRing", () => {
  it("expands the ring geometry by the same pixel distance on each side", () => {
    const spread = 16;
    const radius = 12;
    const { inset, radius: expandedRadius } = getPulseExpansionGeometry(radius, spread);

    expect(inset).toBe(-spread);
    expect(expandedRadius).toBe(radius + spread);
  });

  it("passes radius-aware pulse geometry variables to the rendered ring", () => {
    render(<PulsingRing rect={new DOMRect(0, 0, 300, 40)} />);

    expect(document.head.textContent).toContain("--task-tour-pulse-inset:-16px");
    expect(document.head.textContent).toContain("--task-tour-pulse-radius:28px");
  });
});
