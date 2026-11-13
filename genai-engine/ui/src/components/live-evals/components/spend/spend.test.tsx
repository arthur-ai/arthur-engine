import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ContinuousEvalSpendCards, describeEstimateFormula, SpendCards, SpendEstimateLine, SpendEstimateText } from ".";

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
  spent_today: 0.03,
  daily_cost_cap_usd: null,
  cap_reached: false,
};

// Hoisted so the mock factory, which vitest lifts above the imports, can close over it.
// The shape a partial-match replay returned for /spend and /spend_estimate.
const malformed = vi.hoisted(() => ({ count: 3, page: 0, results: [] }));
// What /spend returns; a test may swap in a well-formed response.
const spendReply = vi.hoisted(() => ({ data: malformed as unknown }));

vi.mock("../../hooks/useContinuousEvalSpend", () => ({
  useContinuousEvalSpend: () => ({ data: spendReply.data, isLoading: false }),
  useContinuousEvalSpendEstimate: () => ({ data: malformed, isFetching: false }),
}));

// A non-USD display currency: spend amounts are USD and must not take its symbol.
vi.mock("@/contexts/DisplaySettingsContext", () => ({
  useDisplaySettings: () => ({ defaultCurrency: "EUR" }),
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

  it("says the judge was called but has no price when every run is unpriced", () => {
    render(
      <SpendCards
        spend={{
          ...spend,
          estimate: {
            ...estimate,
            run_count: 0,
            unpriced_run_count: 3,
            average_run_cost: null,
            estimated_daily_cost: null,
            unavailable_reason: "no_runs",
          },
        }}
        currency="USD"
      />
    );

    expect(screen.getByText("3 runs called the LLM in the last 7 days, but its model has no price")).toBeTruthy();
  });

  it("says there are no runs since the evaluator changed after a switch", () => {
    render(
      <SpendCards
        spend={{
          ...spend,
          estimate: {
            ...estimate,
            run_count: 0,
            average_run_cost: null,
            estimated_daily_cost: null,
            unavailable_reason: "no_runs",
            priced_since: "2026-11-03T10:00:00",
          },
        }}
        currency="USD"
      />
    );

    expect(screen.getByText("No runs since the evaluator changed")).toBeTruthy();
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
    const { container } = render(<SpendEstimateLine taskId="task" llmEvalName="evaluator" llmEvalVersion="latest" samplePercent="50" />);

    expect(container.innerHTML).toBe("");
  });
});

describe("spend currency", () => {
  it("shows USD amounts in USD when the display currency is another one", () => {
    spendReply.data = { ...spend, daily_cost_cap_usd: 10, spent_today: 1.2, cap_reached: false };
    try {
      render(<ContinuousEvalSpendCards evalId="22222222-2222-4222-8222-222222222222" />);
    } finally {
      spendReply.data = malformed;
    }

    expect(screen.getByText("since midnight, of $10.000000 daily cap")).toBeTruthy();
    expect(document.body.textContent).not.toContain("€");
  });
});

describe("daily cap", () => {
  it("shows no cap card or pause note without a cap", () => {
    render(<SpendCards spend={spend} currency="USD" />);
    expect(screen.queryByText("Spent today")).toBeNull();
    expect(screen.queryByText(/Paused for today/)).toBeNull();
  });

  it("shows today's spend against the cap", () => {
    render(<SpendCards spend={{ ...spend, daily_cost_cap_usd: 1, spent_today: 0.25 }} currency="USD" />);
    expect(screen.getByText("Spent today")).toBeTruthy();
    expect(screen.getByText(/daily cap$/)).toBeTruthy();
    expect(screen.queryByText(/Paused for today/)).toBeNull();
  });

  it("shows the pause note once the cap is reached", () => {
    render(<SpendCards spend={{ ...spend, daily_cost_cap_usd: 1, spent_today: 1.2, cap_reached: true }} currency="USD" />);
    expect(screen.getByText(/Paused for today/)).toBeTruthy();
  });
});

describe("estimate accuracy notes", () => {
  it("shows the share of traces that reach the judge when some are skipped", () => {
    const text = describeEstimateFormula({ ...estimate, judged_share: 0.6 }, "USD");
    expect(text).toContain("60% reach the judge");
  });

  it("says the price comes from the current evaluator after a switch", () => {
    const text = describeEstimateFormula({ ...estimate, priced_since: "2026-11-03T10:00:00" }, "USD");
    expect(text).toContain("runs since the evaluator changed");
  });

  it("leaves both out when every trace is judged and the evaluator never changed", () => {
    const text = describeEstimateFormula({ ...estimate, judged_share: 1, priced_since: null }, "USD");
    expect(text).not.toContain("reach the judge");
    expect(text).not.toContain("evaluator changed");
  });
});
describe("trace filter share in the estimate", () => {
  it("states the share of recent traces that match the filter", () => {
    const text = describeEstimateFormula({ ...estimate, filter_match_share: 0.25, filter_traces_checked: 200 }, "USD");
    expect(text).toBe("2 traces/day × 50% sampled × 25% match the filter (of 200 recent traces) × $0.040000 per run (last 7 days)");
  });

  it("leaves it out without a filter", () => {
    expect(describeEstimateFormula(estimate, "USD")).not.toContain("match the filter");
  });
});
