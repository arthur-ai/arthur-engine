import { describe, expect, it } from "vitest";

import { runLevelsFor } from "../hooks/useContinuousEvalsResults";

import { describeRunTarget } from "./results-columns";

describe("span-scope results", () => {
  it("names what each run judged", () => {
    expect(describeRunTarget({ run_level: "trace" })).toBe("Trace");
    expect(describeRunTarget({})).toBe("Trace");
    expect(describeRunTarget({ run_level: "span_rollup" })).toBe("Trace, from its spans");
    expect(describeRunTarget({ run_level: "span", span_id: "call-1" })).toBe("Span call-1");
  });

  it("lists one verdict per trace unless span runs are asked for", () => {
    expect(runLevelsFor(false)).toEqual(["trace", "span_rollup"]);
    expect(runLevelsFor(true)).toBeUndefined();
  });
});
