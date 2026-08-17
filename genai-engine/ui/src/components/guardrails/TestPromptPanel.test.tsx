import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TestPromptPanel } from "./TestPromptPanel";

const renderPanel = (onValidate = vi.fn().mockResolvedValue({ results: [] })) =>
  render(
    <TestPromptPanel
      onValidate={onValidate}
      onResetResults={vi.fn()}
      validating={false}
      results={null}
      error={null}
      hasEnabledRules
      enabledRuleTypes={["KeywordRule"]}
    />
  );

describe("TestPromptPanel", () => {
  it("keeps oversized multiline inputs in the same scroll region as the form", () => {
    renderPanel();

    const prompt = "A very long prompt\n".repeat(100);
    const response = "A very long response\n".repeat(100);
    const context = "A very long context\n".repeat(100);

    fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: prompt } });
    fireEvent.change(screen.getByLabelText("Response"), { target: { value: response } });
    fireEvent.change(screen.getByLabelText("Context"), { target: { value: context } });

    const scrollContainer = screen.getByTestId("test-prompt-scroll-container");
    expect(getComputedStyle(scrollContainer).overflowY).toBe("auto");
    expect(getComputedStyle(scrollContainer).paddingTop).toBe("12px");
    expect(scrollContainer.contains(screen.getByRole("button", { name: "Validate" }))).toBe(true);
    expect((screen.getByLabelText("Prompt") as HTMLTextAreaElement).value).toBe(prompt);
  });

  it("exposes an accessible Validate button and submits all field values", () => {
    const onValidate = vi.fn().mockResolvedValue({ results: [] });
    renderPanel(onValidate);

    const validateButton = screen.getByRole("button", { name: "Validate" }) as HTMLButtonElement;
    expect(validateButton.disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Prompt"), { target: { value: "prompt value" } });
    fireEvent.change(screen.getByLabelText("Response"), { target: { value: "response value" } });
    fireEvent.change(screen.getByLabelText("Context"), { target: { value: "context value" } });
    expect(validateButton.disabled).toBe(false);

    fireEvent.click(validateButton);

    expect(onValidate).toHaveBeenCalledWith({
      prompt: "prompt value",
      response: "response value",
      context: "context value",
    });
  });
});
