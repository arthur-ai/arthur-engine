import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CLAUDE_HAIKU_4_5, CLAUDE_SONNET_5_5, GPT_4O_MINI, GPT_5_MINI } from "./reasoningOptionsFixtures.test-utils";
import { EMPTY_REASONING_SETTINGS } from "./reasoningSettings";
import ReasoningSettingsFields from "./ReasoningSettingsFields";

const optionNames = (comboboxName: string) => {
  fireEvent.mouseDown(screen.getByRole("combobox", { name: comboboxName }));
  const listbox = screen.getAllByRole("listbox").at(-1)!;
  return within(listbox)
    .getAllByRole("option")
    .map((option) => [option.textContent, option.getAttribute("aria-disabled") === "true"]);
};

describe("ReasoningSettingsFields", () => {
  it("shows only the efforts the model accepts", () => {
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} options={GPT_5_MINI} modelChosen />);
    expect(screen.queryByRole("combobox", { name: "Thinking" })).toBeNull();
    expect(optionNames("Reasoning effort")).toEqual([
      ["Provider default", false],
      ["minimal", false],
      ["low", false],
      ["medium", false],
      ["high", false],
    ]);
  });

  it("offers thinking off where it works", () => {
    const onChange = vi.fn();
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={onChange} options={CLAUDE_HAIKU_4_5} modelChosen />);

    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Thinking" }));
    fireEvent.click(within(screen.getByRole("listbox")).getByRole("option", { name: "Off" }));

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" });
    expect(screen.getByText(/model provider's default for evals/)).toBeTruthy();
  });

  it("leaves off out for always-thinking models and says to use effort low", () => {
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} options={CLAUDE_SONNET_5_5} modelChosen />);
    expect(screen.getByText(/can't be turned off for this model. Use reasoning effort low/)).toBeTruthy();
    expect(optionNames("Thinking").map(([name]) => name)).toEqual(["Provider default", "Adaptive", "On, with a token budget"]);
  });

  it("keeps a saved value the model refuses, disabled, with the error", () => {
    render(
      <ReasoningSettingsFields value={{ ...EMPTY_REASONING_SETTINGS, reasoningEffort: "none" }} onChange={vi.fn()} options={GPT_5_MINI} modelChosen />
    );
    expect(screen.getByText(/"none" isn't supported by this model/)).toBeTruthy();
    expect(optionNames("Reasoning effort").at(-1)).toEqual(["none", true]);
  });

  it("says when the model takes no reasoning settings", () => {
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} options={GPT_4O_MINI} modelChosen />);
    expect(screen.getByText(/doesn't take reasoning settings/)).toBeTruthy();
  });

  it("renders nothing before a model is chosen", () => {
    const { container } = render(
      <ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} options={undefined} modelChosen={false} />
    );
    expect(container.textContent).toBe("");
  });

  it("asks for a budget only when thinking is on", () => {
    const { rerender } = render(
      <ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} options={CLAUDE_HAIKU_4_5} modelChosen />
    );
    expect(screen.queryByLabelText("Thinking budget (tokens)")).toBeNull();

    rerender(
      <ReasoningSettingsFields
        value={{ ...EMPTY_REASONING_SETTINGS, thinkingMode: "enabled", budgetTokens: "100" }}
        onChange={vi.fn()}
        options={CLAUDE_HAIKU_4_5}
        modelChosen
      />
    );
    expect(screen.getByLabelText("Thinking budget (tokens)")).toBeTruthy();
    expect(screen.getByText(/at least 1024 tokens/)).toBeTruthy();
  });
});
