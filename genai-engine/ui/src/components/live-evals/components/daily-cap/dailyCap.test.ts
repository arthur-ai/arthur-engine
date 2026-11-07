import { describe, expect, it } from "vitest";

import { dailyCapSchema, dailyCapToUsd, usdToDailyCap } from "./dailyCap";

describe("daily cap conversion", () => {
  it("maps an empty field to no cap", () => {
    expect(dailyCapToUsd("")).toBeNull();
    expect(dailyCapToUsd("  ")).toBeNull();
    expect(usdToDailyCap(null)).toBe("");
    expect(usdToDailyCap(undefined)).toBe("");
  });

  it("converts between the field and dollars", () => {
    expect(dailyCapToUsd("2.5")).toBe(2.5);
    expect(usdToDailyCap(10)).toBe("10");
  });
});

describe("dailyCapSchema", () => {
  it.each(["", "0.01", "10", "250.5"])("accepts %j", (value) => {
    expect(dailyCapSchema.safeParse(value).success).toBe(true);
  });

  it.each(["0", "-1", "abc"])("rejects %j", (value) => {
    expect(dailyCapSchema.safeParse(value).success).toBe(false);
  });
});
