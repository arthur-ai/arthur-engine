import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { TraceFilterRow } from "../trace-filter";

import { SpendEstimateLine } from ".";

import type { ContinuousEvalDailySpendEstimate } from "@/lib/api-client/api-client";

const estimate = vi.hoisted((): ContinuousEvalDailySpendEstimate => ({
  window_days: 7,
  trace_count: 14,
  traces_per_day: 2,
  sample_rate: 1,
  run_count: 3,
  average_run_cost: 0.04,
  estimated_daily_cost: 0.08,
  unavailable_reason: null,
}));

vi.mock("../../hooks/useContinuousEvalSpend", () => ({
  useContinuousEvalSpend: () => ({ data: undefined, isLoading: false }),
  useContinuousEvalSpendEstimate: () => ({ data: estimate, isFetching: false }),
}));

vi.mock("@/contexts/DisplaySettingsContext", () => ({
  useDisplaySettings: () => ({ defaultCurrency: "USD" }),
}));

const paid: TraceFilterRow = { spanName: "", attributePath: "attributes.metadata.plan", operator: "equals", value: "paid" };
const blank: TraceFilterRow = { spanName: "", attributePath: "", operator: "equals", value: "" };

describe("SpendEstimateLine with a trace filter", () => {
  it("says when a condition is left out because it isn't filled in", () => {
    render(<SpendEstimateLine taskId="task" llmEvalName="evaluator" samplePercent="" traceFilter={[paid, blank]} />);
    expect(screen.getByText(/1 trace filter condition isn't filled in yet/)).toBeTruthy();
  });

  it("says nothing extra when every condition is complete", () => {
    render(<SpendEstimateLine taskId="task" llmEvalName="evaluator" samplePercent="" traceFilter={[paid]} />);
    expect(screen.queryByText(/filled in yet/)).toBeNull();
  });
});
