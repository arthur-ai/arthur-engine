import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ModelWhitelistSection } from "./index";

// Testing Library's auto-cleanup only registers when vitest runs with `globals:
// true`, and this project does not. Without this, every render stacks in the same
// document and queries match elements from earlier tests.
afterEach(cleanup);

vi.mock("../../../../hooks/useModelWhitelist", () => ({
  useModelWhitelist: () => ({
    data: { provider: "openai", whitelist: null, catalog: ["gpt-5", "gpt-4.1", "gpt-4o"] },
    isLoading: false,
    error: null,
  }),
}));

const CAVEAT = /including models your account may not have access to/;

const baseProps = {
  provider: "openai" as const,
  providerDisplayName: "OpenAI",
  value: null,
  onChange: vi.fn(),
  onInitialValue: vi.fn(),
};

const searchField = () => screen.getByPlaceholderText("Search OpenAI models…");

describe("ModelWhitelistSection", () => {
  it("hides the picker when All models is selected", () => {
    render(<ModelWhitelistSection {...baseProps} />);

    const allModels = screen.getByRole("radio", { name: /All models/ }) as HTMLInputElement;
    expect(allModels.checked).toBe(true);
    expect(screen.queryByPlaceholderText("Search OpenAI models…")).toBeNull();
    expect(screen.queryByText("Select at least one model")).toBeNull();
  });

  it("reports the stored whitelist to the parent exactly once", () => {
    const onInitialValue = vi.fn();
    const { rerender } = render(<ModelWhitelistSection {...baseProps} onInitialValue={onInitialValue} />);
    rerender(<ModelWhitelistSection {...baseProps} onInitialValue={onInitialValue} />);

    expect(onInitialValue).toHaveBeenCalledTimes(1);
    expect(onInitialValue).toHaveBeenCalledWith(null);
  });

  it("switches to a restricted empty list when Only selected is chosen", () => {
    const onChange = vi.fn();
    render(<ModelWhitelistSection {...baseProps} onChange={onChange} />);

    fireEvent.click(screen.getByRole("radio", { name: /Only selected/ }));

    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("clears the selection when switching back to All models", () => {
    const onChange = vi.fn();
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5"]} onChange={onChange} />);

    fireEvent.click(screen.getByRole("radio", { name: /All models/ }));

    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("renders the empty-state alert for an empty selection", () => {
    render(<ModelWhitelistSection {...baseProps} value={[]} />);

    expect(screen.queryByText("Select at least one model")).not.toBeNull();
  });

  it("hides the empty-state alert once a model is selected", () => {
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5"]} />);

    expect(screen.queryByText("Select at least one model")).toBeNull();
    expect(screen.queryByText("gpt-5")).not.toBeNull();
  });

  it("warns how many models a save would hide", () => {
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5"]} />);

    // 3 in the catalog, 1 selected.
    expect(screen.queryByText(/^2 models will be hidden\./)).not.toBeNull();
  });

  it("shows the catalog caveat inside the dropdown, once opened", () => {
    // All models: no picker at all, so there is no dropdown to open.
    const { unmount } = render(<ModelWhitelistSection {...baseProps} />);
    expect(screen.queryByText(CAVEAT)).toBeNull();
    unmount();

    // Only selected: the caveat lives in the Autocomplete's Paper, which MUI mounts
    // only while the popup is open — closed is the correct initial state.
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5"]} />);
    expect(screen.queryByText(CAVEAT)).toBeNull();

    fireEvent.mouseDown(searchField());

    expect(screen.queryByText(CAVEAT)).not.toBeNull();
  });
});
