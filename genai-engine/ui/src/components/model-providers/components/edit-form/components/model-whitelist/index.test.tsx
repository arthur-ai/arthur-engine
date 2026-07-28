import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ModelWhitelistSection } from "./index";

// Auto-cleanup only registers under vitest `globals: true`, which this project does
// not set, so renders would otherwise stack in one document across tests.
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
  providerEnabled: false,
  value: null,
  onChange: vi.fn(),
  onInitialValue: vi.fn(),
};

const searchField = () => screen.getByPlaceholderText("Search OpenAI models…");

describe("ModelWhitelistSection", () => {
  it("renders during first-time setup for a provider with a static catalog", () => {
    render(<ModelWhitelistSection {...baseProps} />);

    expect(screen.queryByText("Visible models")).not.toBeNull();
  });

  it("renders nothing for an unconfigured vLLM, whose catalog needs a saved api_base", () => {
    render(<ModelWhitelistSection {...baseProps} provider="hosted_vllm" providerDisplayName="vLLM" providerEnabled={false} />);

    expect(screen.queryByText("Visible models")).toBeNull();
    expect(screen.queryByText(/Couldn't load/)).toBeNull();
  });

  it("renders for vLLM once it is configured", () => {
    render(<ModelWhitelistSection {...baseProps} provider="hosted_vllm" providerDisplayName="vLLM" providerEnabled />);

    expect(screen.queryByText("Visible models")).not.toBeNull();
  });

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

  it("shows the catalog caveat inside the dropdown, once opened", () => {
    const { unmount } = render(<ModelWhitelistSection {...baseProps} />);
    expect(screen.queryByText(CAVEAT)).toBeNull();
    unmount();

    // The caveat lives in the Autocomplete's Paper, which MUI mounts only while the
    // popup is open.
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5"]} />);
    expect(screen.queryByText(CAVEAT)).toBeNull();

    fireEvent.mouseDown(searchField());

    expect(screen.queryByText(CAVEAT)).not.toBeNull();
  });

  it("keeps the search placeholder visible when models are selected", () => {
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5", "gpt-4.1"]} />);

    expect(searchField()).not.toBeNull();
    expect(screen.queryByText("gpt-5")).not.toBeNull();
    expect(screen.queryByText("gpt-4.1")).not.toBeNull();
  });

  it("removes a model when its chip is deleted", () => {
    const onChange = vi.fn();
    render(<ModelWhitelistSection {...baseProps} value={["gpt-5", "gpt-4.1"]} onChange={onChange} />);

    // MUI renders the delete affordance as an svg inside the chip, not a button, so
    // there is no accessible role to target — reach it through the chip root.
    const chip = screen.getByText("gpt-5").closest(".MuiChip-root");
    const deleteIcon = chip?.querySelector(".MuiChip-deleteIcon");
    expect(deleteIcon).not.toBeNull();
    fireEvent.click(deleteIcon as Element);

    expect(onChange).toHaveBeenCalledWith(["gpt-4.1"]);
  });
});
