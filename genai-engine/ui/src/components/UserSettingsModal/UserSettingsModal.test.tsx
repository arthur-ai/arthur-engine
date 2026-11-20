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
  initialSettings: {
    timezone: "UTC",
    use24Hour: false,
    enableChatbot: true,
    blacklistEndpoints: [],
  },
};

// A stable array: the default [] is a new one each render, which re-runs the
// reset-on-open effect and would undo a change made in the test.
const RETENTION_DAYS = [90];

describe("UserSettingsModal", () => {
  it("shows the default model with no model picker", () => {
    const onOpenModelProviders = vi.fn();
    render(<UserSettingsModal {...baseProps} defaultModelLabel="openai · gpt-4.1-mini" onOpenModelProviders={onOpenModelProviders} />);

    expect(screen.getByText("openai · gpt-4.1-mini")).toBeTruthy();
    expect(screen.queryByLabelText("Model Provider")).toBeNull();
    expect(screen.queryByLabelText("Model Name")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Change" }));
    expect(onOpenModelProviders).toHaveBeenCalled();
  });

  it("warns when no default model is set and links to Model Providers", () => {
    const onOpenModelProviders = vi.fn();
    render(<UserSettingsModal {...baseProps} defaultModelLabel={null} onOpenModelProviders={onOpenModelProviders} />);

    expect(screen.getByText(/No default model is set/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Set default" }));
    expect(onOpenModelProviders).toHaveBeenCalled();
  });

  it("saves the AI Assistant toggle", () => {
    const onSave = vi.fn();
    render(<UserSettingsModal {...baseProps} onSave={onSave} defaultModelLabel="openai · gpt-4.1-mini" allowedTraceRetentionDays={RETENTION_DAYS} />);

    fireEvent.click(screen.getByLabelText("Enable AI Assistant"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ enableChatbot: false }));
  });

  it("saves the insights switch only when it changed", () => {
    const onSave = vi.fn();
    render(
      <UserSettingsModal
        {...baseProps}
        onSave={onSave}
        insightsGenerationAvailable
        initialInsightsGenerationEnabled={false}
        allowedTraceRetentionDays={RETENTION_DAYS}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenLastCalledWith(expect.objectContaining({ insightsGenerationEnabled: undefined }));

    fireEvent.click(screen.getByLabelText("Generate insights"));
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenLastCalledWith(expect.objectContaining({ insightsGenerationEnabled: true }));
  });

  it("shows the insights switch when the AI Assistant is off on the server", () => {
    render(<UserSettingsModal {...baseProps} chatbotEnabled={false} insightsGenerationAvailable defaultModelLabel={null} />);

    expect(screen.getByLabelText("Generate insights")).toBeTruthy();
    expect(screen.queryByLabelText("Enable AI Assistant")).toBeNull();
    expect(screen.getByText(/No default model is set/)).toBeTruthy();
  });
});
