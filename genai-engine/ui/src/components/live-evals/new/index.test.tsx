import { describe, expect, it } from "vitest";

import { getInitialEvaluatorState } from ".";

describe("LiveEvalsNewForm URL defaults", () => {
  it("initializes an LLM evaluator type when an evaluator is pre-filled", () => {
    const searchParams = new URLSearchParams({ evalName: "helpfulness", evalVersion: "3" });
    expect(getInitialEvaluatorState(searchParams)).toEqual({
      name: "helpfulness",
      version: "3",
      eval_type: "llm_as_a_judge",
    });
  });

  it("keeps ML URL defaults ahead of the LLM URL defaults", () => {
    const searchParams = new URLSearchParams({ mlEvalName: "fraud", evalName: "helpfulness", evalVersion: "3" });
    expect(getInitialEvaluatorState(searchParams)).toEqual({
      name: "fraud",
      version: "latest",
      eval_type: "ml",
    });
  });

  it("does not select an evaluator type without an evaluator name", () => {
    const searchParams = new URLSearchParams();
    expect(getInitialEvaluatorState(searchParams).eval_type).toBeNull();
  });
});
