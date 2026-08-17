import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserSettingsModal } from "./UserSettingsModal";

// Auto-cleanup only registers under vitest `globals: true`, which this project does
// not set, so renders would otherwise stack in one document across tests.
afterEach(cleanup);

const baseProps = {
  open: true,
  onClose: vi.fn(),
  onSave: vi.fn(),
  chatbotEnabled: true,
  enabledProviders: ["openai" as const],
  initialSettings: {
    timezone: "UTC",
    use24Hour: false,
    enableChatbot: true,
    chatbotModelProvider: "openai" as const,
    chatbotModelName: "gpt-4o",
    blacklistEndpoints: [],
  },
};

const openModelSelect = () => {
  fireEvent.mouseDown(screen.getByLabelText("Model Name"));
};

describe("UserSettingsModal", () => {
  it("keeps a model that is no longer whitelisted selectable, shown as-is", () => {
    render(<UserSettingsModal {...baseProps} availableModelsMap={new Map([["openai", ["gpt-5"]]])} />);

    openModelSelect();

    const stale = screen.getByRole("option", { name: "gpt-4o" });
    expect(stale.getAttribute("aria-disabled")).toBeNull();
    expect(screen.queryByText(/no longer listed/)).toBeNull();
  });

  it("does not duplicate a model that is still whitelisted", () => {
    render(<UserSettingsModal {...baseProps} availableModelsMap={new Map([["openai", ["gpt-4o", "gpt-5"]]])} />);

    openModelSelect();

    expect(screen.getAllByRole("option", { name: "gpt-4o" })).toHaveLength(1);
  });
});
