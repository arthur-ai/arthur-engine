import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TracingFilterModal } from "./TracingFilterModal";

const setFilters = vi.fn();

vi.mock("../../../stores/filter.store", () => ({
  useFilterStore: (selector: (state: { filters: never[]; setFilters: typeof setFilters }) => unknown) =>
    selector({ filters: [], setFilters }),
}));

vi.mock("@/components/live-evals/hooks/useContinuousEvals", () => ({
  useInfiniteContinuousEvals: () => ({
    data: undefined,
    fetchNextPage: vi.fn(),
    hasNextPage: false,
    isFetchingNextPage: false,
  }),
}));

vi.mock("@mui/x-date-pickers/DateTimePicker", () => ({
  DateTimePicker: () => null,
}));

describe("TracingFilterModal", () => {
  beforeEach(() => {
    setFilters.mockClear();
  });

  const openModal = () => {
    render(<TracingFilterModal />);
    fireEvent.click(screen.getByRole("button", { name: "Filter" }));
  };

  it("applies an uncommitted Session ID when Apply Filters is clicked", async () => {
    openModal();

    fireEvent.change(screen.getByPlaceholderText("Enter Session ID"), { target: { value: " session-123 " } });
    fireEvent.click(screen.getByRole("button", { name: "Apply Filters" }));

    await waitFor(() => expect(setFilters).toHaveBeenCalledWith([{ name: "session_ids", operator: "in", value: ["session-123"] }]));
  });

  it("turns pasted IDs into chips without inserting the pasted text", () => {
    openModal();

    const input = screen.getByPlaceholderText("Enter Session ID");
    fireEvent.paste(input, { clipboardData: { getData: () => "session-pasted" } });

    expect(screen.getByText("session-pasted")).toBeTruthy();
    expect(input).toHaveProperty("value", "");
  });
});
