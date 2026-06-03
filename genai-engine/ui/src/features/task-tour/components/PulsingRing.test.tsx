import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PulsingRing } from "./PulsingRing";

describe("PulsingRing", () => {
  it("passes radius-aware pulse geometry variables to the rendered ring", () => {
    render(<PulsingRing rect={new DOMRect(0, 0, 300, 40)} />);

    expect(document.head.textContent).toContain("--task-tour-pulse-inset:-16px");
    expect(document.head.textContent).toContain("--task-tour-pulse-radius:28px");
  });
});
