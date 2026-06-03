import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Results } from ".";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";

const queryState = vi.hoisted(() => ({
  values: new Map<string, string | null>(),
}));

vi.mock("nuqs", () => ({
  parseAsString: {
    withDefault: () => ({}),
  },
  parseAsStringEnum: () => ({}),
  useQueryState: (key: string) => {
    const [value, setValue] = React.useState(queryState.values.get(key) ?? "");
    return [
      value,
      (next: string | null) => {
        queryState.values.set(key, next);
        setValue(next ?? "");
      },
    ] as const;
  },
}));

vi.mock("@arthur/shared-components", () => ({
  TextOperators: {
    CONTAINS: "contains",
  },
  TracesEmptyState: ({ title }: { title: string }) => <div>{title}</div>,
}));

vi.mock("@tanstack/react-query", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@tanstack/react-query")>();
  return {
    ...actual,
    useSuspenseQuery: () => ({
      data: {
        annotations: [
          {
            id: "annotation-id",
            eval_name: "Readability",
          },
        ],
        count: 1,
      },
    }),
  };
});

vi.mock("../../data/results-columns", () => ({
  createColumns: () => [
    {
      accessorKey: "eval_name",
      header: "Eval",
      cell: ({ getValue }: { getValue: () => string }) => getValue(),
    },
  ],
}));

vi.mock("./components/details", () => ({
  Details: ({ onClose }: { onClose: () => void }) => <button onClick={onClose}>Close details</button>,
}));

vi.mock("./components/FilterModal", () => ({
  FilterModal: () => <button>Filter</button>,
}));

vi.mock("@/components/traces/stores/filter.store", () => ({
  useFilterStore: (selector: (state: { filters: unknown[]; setFilters: () => void }) => unknown) => selector({ filters: [], setFilters: vi.fn() }),
}));

vi.mock("@/contexts/DisplaySettingsContext", () => ({
  useDisplaySettings: () => ({ defaultCurrency: "USD" }),
}));

vi.mock("@/hooks/useApi", () => ({
  useApi: () => ({}),
}));

vi.mock("@/hooks/useTask", () => ({
  useTask: () => ({ task: { id: "task-id" } }),
}));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    evaluateResultDetailsReviewed: "task-tour:evaluate-result-details-reviewed",
  },
}));

describe("Evaluate Results task tour target", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryState.values.clear();
  });

  it("highlights the first row and completes after the details dialog is closed", async () => {
    render(<Results />);

    const row = screen.getByRole("row", { name: /readability/i });
    expect(row.getAttribute("data-tour-id")).toBe(TOUR_IDS.evaluateResultsFirstRow);

    fireEvent.click(row);

    expect(screen.getByRole("dialog").getAttribute("data-tour-id")).toBe(TOUR_IDS.evaluateResultsDetailsDialog);
    await waitFor(() => expect(refreshTaskTourTarget).toHaveBeenCalledTimes(1));
    expect(dispatchTourEvent).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /close details/i }));

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.evaluateResultDetailsReviewed);
  });
});
