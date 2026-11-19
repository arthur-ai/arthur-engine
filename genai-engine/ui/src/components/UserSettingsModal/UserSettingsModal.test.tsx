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

const RETENTION_DAYS = [90];

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

  it("shows the default model choice for a chatbot that follows the default", () => {
    const onSave = vi.fn();
    render(
      <UserSettingsModal
        {...baseProps}
        onSave={onSave}
        defaultModelLabel="openai · gpt-4.1-mini"
        initialSettings={{ ...baseProps.initialSettings, chatbotUseDefaultModel: true }}
      />
    );

    expect(screen.getByText("Default model · openai · gpt-4.1-mini")).toBeTruthy();
    expect(screen.queryByLabelText("Model Name")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ chatbotUseDefaultModel: true }));
  });

  it("leaves the default when a provider is picked", () => {
    const onSave = vi.fn();
    render(
      <UserSettingsModal
        {...baseProps}
        onSave={onSave}
        availableModelsMap={new Map([["openai", ["gpt-4o"]]])}
        // a stable array: the default [] is a new one each render, which re-runs the
        // reset-on-open effect and would undo the pick
        allowedTraceRetentionDays={RETENTION_DAYS}
        initialSettings={{ ...baseProps.initialSettings, chatbotUseDefaultModel: true }}
      />
    );

    fireEvent.mouseDown(screen.getByLabelText("Model Provider"));
    fireEvent.click(screen.getByRole("option", { name: "openai" }));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ chatbotUseDefaultModel: false, chatbotModelProvider: "openai" }));
  });
});
