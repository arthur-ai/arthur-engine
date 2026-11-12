import { describe, expect, it } from "vitest";

import { validateTransform } from "./transformBuilder";

describe("validateTransform", () => {
  it("accepts a whole-trace variable, which has no span or attribute path", () => {
    expect(validateTransform({ variables: [{ variable_name: "conversation", source: "trace", attribute_path: "" }] })).toEqual([]);
  });

  it("still needs a span and a path for a span variable", () => {
    expect(validateTransform({ variables: [{ variable_name: "v", attribute_path: "" }] })).toEqual([
      "Variable v: span_name or span_kind is required",
      "Variable v: attribute_path is required",
    ]);
  });
});
