import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PulsingRing } from "./PulsingRing";

describe("PulsingRing", () => {
  it("drives the pulse with transform + opacity so it works in Safari (UP-4494)", () => {
    render(<PulsingRing rect={new DOMRect(0, 0, 300, 40)} />);
    const styles = document.head.textContent ?? "";

    // The ring must emanate via a GPU-composited transform that scales up...
    expect(styles).toContain("transform:scale(1)");
    expect(styles).toMatch(/transform:scale\(1\.\d+\)/);
    // ...fading out and HOLDING at opacity 0 so the loop reset is invisible.
    expect(styles).toContain("opacity:0.85");
    expect(styles).toMatch(/opacity:0[;}]/);

    // Regression guard: Safari (WebKit) does not interpolate keyframe values
    // that resolve through unregistered CSS custom properties or `inherit`,
    // so the pulse must not depend on animated `var(--task-tour-pulse-*)`
    // values — that left only an in-place opacity blink on Safari.
    expect(styles).not.toContain("var(--task-tour-pulse");
  });
});
