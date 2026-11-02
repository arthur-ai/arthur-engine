import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EMPTY_REASONING_SETTINGS } from "./reasoningSettings";
import ReasoningSettingsFields from "./ReasoningSettingsFields";

describe("ReasoningSettingsFields", () => {
  it("offers thinking off for Anthropic", () => {
    const onChange = vi.fn();
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={onChange} provider="anthropic" modelName="claude-haiku-4-5" />);

    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Thinking" }));
    fireEvent.click(within(screen.getByRole("listbox")).getByRole("option", { name: "Off" }));

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_REASONING_SETTINGS, thinkingMode: "disabled" });
  });

  it("hides thinking for Gemini on Vertex AI", () => {
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} provider="vertex_ai" modelName="gemini-2.5-flash" />);
    expect(screen.queryByRole("combobox", { name: "Thinking" })).toBeNull();
  });

  it("hides thinking for OpenAI and leaves 'default' out of the effort choices", () => {
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} provider="openai" modelName="gpt-5-mini" />);

    expect(screen.queryByRole("combobox", { name: "Thinking" })).toBeNull();
    fireEvent.mouseDown(screen.getByRole("combobox", { name: "Reasoning effort" }));
    const options = within(screen.getByRole("listbox"))
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(options).toEqual(["Provider default", "none", "minimal", "low", "medium", "high"]);
  });

  it("explains that unset settings fall back to the provider default", () => {
    render(<ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} provider="anthropic" modelName="claude-haiku-4-5" />);
    expect(screen.getByText(/model provider's default for evals/)).toBeTruthy();
  });

  it("asks for a budget only when thinking is on", () => {
    const { rerender } = render(
      <ReasoningSettingsFields value={EMPTY_REASONING_SETTINGS} onChange={vi.fn()} provider="anthropic" modelName="claude-haiku-4-5" />
    );
    expect(screen.queryByLabelText("Thinking budget (tokens)")).toBeNull();

    rerender(
      <ReasoningSettingsFields
        value={{ ...EMPTY_REASONING_SETTINGS, thinkingMode: "enabled", budgetTokens: "100" }}
        onChange={vi.fn()}
        provider="anthropic"
        modelName="claude-haiku-4-5"
      />
    );
    expect(screen.getByLabelText("Thinking budget (tokens)")).toBeTruthy();
    expect(screen.getByText(/at least 1024 tokens/)).toBeTruthy();
  });
});
