import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ContinuousEvalSpendCards, SpendCards, SpendEstimateLine, SpendEstimateText } from ".";

import type { ContinuousEvalDailySpendEstimate, ContinuousEvalSpendResponse } from "@/lib/api-client/api-client";

const estimate: ContinuousEvalDailySpendEstimate = {
  window_days: 7,
  trace_count: 14,
  traces_per_day: 2,
  sample_rate: 0.5,
  run_count: 3,
  average_run_cost: 0.04,
  estimated_daily_cost: 0.04,
  unavailable_reason: null,
};

const spend: ContinuousEvalSpendResponse = {
  continuous_eval_id: "22222222-2222-4222-8222-222222222222",
  last_24h_run_count: 5,
  last_24h_cost: 0.06,
  estimate,
};

// Hoisted so the mock factory, which vitest lifts above the imports, can close over it.
// The shape a partial-match replay returned for /spend and /spend_estimate.
const malformed = vi.hoisted(() => ({ count: 3, page: 0, results: [] }));

vi.mock("../../hooks/useContinuousEvalSpend", () => ({
  useContinuousEvalSpend: () => ({ data: malformed, isLoading: false }),
  useContinuousEvalSpendEstimate: () => ({ data: malformed, isFetching: false }),
}));

vi.mock("@/contexts/DisplaySettingsContext", () => ({
  useDisplaySettings: () => ({ defaultCurrency: "USD" }),
}));

describe("SpendCards", () => {
  it("shows the last 24 hours and the daily estimate with its formula", () => {
    render(<SpendCards spend={spend} currency="USD" />);

    expect(screen.getByText("Last 24 hours")).toBeTruthy();
    expect(screen.getByText("$0.060000")).toBeTruthy();
    expect(screen.getByText("5 runs")).toBeTruthy();
    expect(screen.getByText("Estimated per day")).toBeTruthy();
    expect(screen.getByText("$0.040000")).toBeTruthy();
    expect(screen.getByText("2 traces/day × 50% sampled × $0.040000 per run (last 7 days)")).toBeTruthy();
  });

  it("shows zero spend and why there is no estimate", () => {
    render(
      <SpendCards
        spend={{
          ...spend,
          last_24h_run_count: 0,
          last_24h_cost: 0,
          estimate: { ...estimate, run_count: 0, average_run_cost: null, estimated_daily_cost: null, unavailable_reason: "no_runs" },
        }}
        currency="USD"
      />
    );

    expect(screen.getByText("$0.00")).toBeTruthy();
    expect(screen.getByText("0 runs")).toBeTruthy();
    expect(screen.getByText("—")).toBeTruthy();
    expect(screen.getByText("No runs that called the LLM in the last 7 days")).toBeTruthy();
  });
});

describe("SpendEstimateText", () => {
  it("states the estimate and how it was computed", () => {
    render(<SpendEstimateText estimate={{ ...estimate, sample_rate: 0.25, estimated_daily_cost: 0.02 }} currency="USD" />);

    expect(screen.getByText("$0.020000 per day")).toBeTruthy();
    expect(screen.getByText(/2 traces\/day × 25% sampled × \$0\.040000 per run \(last 7 days\)/)).toBeTruthy();
  });

  it("explains a task without traffic", () => {
    render(
      <SpendEstimateText
        estimate={{ ...estimate, trace_count: 0, traces_per_day: 0, estimated_daily_cost: null, unavailable_reason: "no_traces" }}
        currency="USD"
      />
    );

    expect(screen.getByText("No cost estimate yet. No traces in the last 7 days.")).toBeTruthy();
  });
});

describe("malformed spend responses", () => {
  it("renders no spend cards", () => {
    const { container } = render(<ContinuousEvalSpendCards evalId="22222222-2222-4222-8222-222222222222" />);

    expect(container.innerHTML).toBe("");
  });

  it("renders no estimate line", () => {
    const { container } = render(<SpendEstimateLine taskId="task" llmEvalName="evaluator" samplePercent="50" />);

    expect(container.innerHTML).toBe("");
  });
});
