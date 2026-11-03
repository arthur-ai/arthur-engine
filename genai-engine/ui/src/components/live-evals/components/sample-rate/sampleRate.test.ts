import { describe, expect, it } from "vitest";

import { percentToSampleRate, samplePercentSchema, sampleRateToPercent } from "./sampleRate";

describe("sample rate conversion", () => {
  it("maps an empty field to every trace", () => {
    expect(percentToSampleRate("")).toBeNull();
    expect(percentToSampleRate("  ")).toBeNull();
    expect(sampleRateToPercent(null)).toBe("");
    expect(sampleRateToPercent(undefined)).toBe("");
  });

  it("converts between percent and rate", () => {
    expect(percentToSampleRate("10")).toBe(0.1);
    expect(percentToSampleRate("100")).toBe(1);
    expect(sampleRateToPercent(0.25)).toBe("25");
    expect(sampleRateToPercent(0.333)).toBe("33.3");
    expect(sampleRateToPercent(1)).toBe("100");
  });
});

describe("samplePercentSchema", () => {
  it.each(["", "1", "12.5", "100"])("accepts %j", (value) => {
    expect(samplePercentSchema.safeParse(value).success).toBe(true);
  });

  it.each(["0", "0.5", "101", "-5", "abc"])("rejects %j", (value) => {
    expect(samplePercentSchema.safeParse(value).success).toBe(false);
  });
});
