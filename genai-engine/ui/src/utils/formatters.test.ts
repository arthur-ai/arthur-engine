import { describe, expect, it } from "vitest";

import { formatDurationMs } from "./formatters";

describe("formatDurationMs", () => {
  it("rounds floating-point millisecond artifacts to whole ms", () => {
    expect(formatDurationMs(302.40099999999995)).toBe("302ms");
  });

  it("formats millisecond-scale values as integers", () => {
    expect(formatDurationMs(0)).toBe("0ms");
    expect(formatDurationMs(999.4)).toBe("999ms");
    expect(formatDurationMs(999.6)).toBe("1.00s");
  });

  it("formats second-scale values", () => {
    expect(formatDurationMs(1000)).toBe("1.00s");
    expect(formatDurationMs(3600)).toBe("3.60s");
    expect(formatDurationMs(26100)).toBe("26.10s");
    expect(formatDurationMs(59_999)).toBe("60.00s");
  });

  it("formats minute-scale values", () => {
    expect(formatDurationMs(60_000)).toBe("1.00m");
    expect(formatDurationMs(90_000)).toBe("1.50m");
  });

  it("returns a dash for non-finite input", () => {
    expect(formatDurationMs(NaN)).toBe("-");
    expect(formatDurationMs(Infinity)).toBe("-");
  });
});
