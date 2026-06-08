import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PulsingRing } from "./PulsingRing";

describe("PulsingRing", () => {
  it("animates with transform scale and opacity, no CSS custom properties", () => {
    render(<PulsingRing rect={new DOMRect(100, 50, 300, 40)} />);

    const styles = document.head.textContent ?? "";

    expect(styles).toContain("scale(1)");
    expect(styles).toMatch(/scale\(\d+(\.\d+)?,\s*\d+(\.\d+)?\)/);

    expect(styles).toContain("opacity:0.8");
    expect(styles).toContain("opacity:0");

    expect(styles).toContain("box-shadow");

    expect(styles).not.toContain("var(--task-tour-pulse");
  });
});
