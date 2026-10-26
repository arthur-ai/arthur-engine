import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Testing Library only registers its automatic unmount when `afterEach` is a global, and
// this config does not enable Vitest globals, so without this every rendered tree stays
// mounted after its test. A still-mounted MUI Dialog/Popover keeps its Fade timers running;
// when one fires after Vitest tears jsdom down, React reads `window` and the run fails with
// "window is not defined" even though every assertion passed.
// Kept out of setup.ts: importing Testing Library loads react-dom, which must happen after
// the AnimationEvent polyfill there.
afterEach(() => {
  cleanup();
});
