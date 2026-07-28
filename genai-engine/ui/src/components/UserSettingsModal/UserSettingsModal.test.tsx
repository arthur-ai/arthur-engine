import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserSettingsModal } from "./UserSettingsModal";

// Testing Library's auto-cleanup only registers when vitest runs with `globals:
// true`, and this project does not. Without this, every render stacks in the same
// document and queries match elements from earlier tests.
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
  // MUI renders Select as a button-like combobox; its menu mounts on open.
  fireEvent.mouseDown(screen.getByLabelText("Model Name"));
};

describe("UserSettingsModal", () => {
  it("keeps a model that is no longer whitelisted visible and disabled", () => {
    render(<UserSettingsModal {...baseProps} availableModelsMap={new Map([["openai", ["gpt-5"]]])} />);

    openModelSelect();

    const stale = screen.getByRole("option", { name: /gpt-4o \(no longer listed\)/ });
    expect(stale.getAttribute("aria-disabled")).toBe("true");
  });

  it("does not mark a still-whitelisted model as unlisted", () => {
    render(<UserSettingsModal {...baseProps} availableModelsMap={new Map([["openai", ["gpt-4o", "gpt-5"]]])} />);

    openModelSelect();

    expect(screen.queryByText(/no longer listed/)).toBeNull();
    expect(screen.queryByRole("option", { name: "gpt-4o" })).not.toBeNull();
  });
});
