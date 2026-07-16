import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { UserSettingsModal } from "./UserSettingsModal";
import type { UserSettingsModalProps } from "./types";

import type { ModelProvider } from "@/lib/api-client/api-client";

const PROVIDER: ModelProvider = "openai";

function renderModal(overrides: Partial<UserSettingsModalProps> = {}) {
  const props: UserSettingsModalProps = {
    open: true,
    onClose: vi.fn(),
    onSave: vi.fn(),
    chatbotEnabled: true,
    enabledProviders: [PROVIDER],
    availableModelsMap: new Map<ModelProvider, string[]>([[PROVIDER, ["gpt-4o"]]]),
    availableEndpoints: ["GET /api/v1/example"],
    initialSettings: { enableChatbot: true },
    ...overrides,
  };
  return render(<UserSettingsModal {...props} />);
}

describe("UserSettingsModal", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows all AI Assistant options when the assistant is enabled", () => {
    renderModal({ initialSettings: { enableChatbot: true } });

    expect(screen.getByText("AI Assistant")).toBeTruthy();
    expect(screen.getByText("Enable AI Assistant")).toBeTruthy();
    // Outlined Select labels render their text in both the <label> and the
    // notched-outline <legend>, so match on presence rather than uniqueness.
    expect(screen.getAllByText("Model Provider").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Model Name").length).toBeGreaterThan(0);
    expect(screen.getByText("Blocked Endpoints")).toBeTruthy();
  });

  it("hides model config and blocked endpoints when the assistant is disabled", () => {
    renderModal({ initialSettings: { enableChatbot: false } });

    expect(screen.getByText("Enable AI Assistant")).toBeTruthy();
    expect(screen.queryByText("Model Provider")).toBeNull();
    expect(screen.queryByText("Model Name")).toBeNull();
    expect(screen.queryByText("Blocked Endpoints")).toBeNull();
  });

  it("does not render the AI Assistant section when chatbot is not enabled on the server", () => {
    renderModal({ chatbotEnabled: false });

    expect(screen.queryByText("AI Assistant")).toBeNull();
    expect(screen.queryByText("Enable AI Assistant")).toBeNull();
  });
});
