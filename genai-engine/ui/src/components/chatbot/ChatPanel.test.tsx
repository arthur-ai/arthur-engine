import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "./ChatPanel";

import { dispatchTaskTourFormPrefill } from "@/features/task-tour/formPrefill";

Element.prototype.scrollIntoView = vi.fn();

afterEach(() => {
  cleanup();
});

function renderPanel(inputTourId = "task-tour-chat-send", panelTourId?: string) {
  return render(
    <ChatPanel
      messages={[]}
      isStreaming={false}
      activeToolCall={null}
      onSend={vi.fn()}
      onAbort={vi.fn()}
      placeholder="Ask the demo agent..."
      inputTourId={inputTourId}
      panelTourId={panelTourId}
    />
  );
}

describe("ChatPanel task tour prefill", () => {
  it("prefills the chat input when the matching tour form prefill is emitted", () => {
    renderPanel();

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: "task-tour-chat-send",
        value: "What is an AI Agent?",
      });
    });

    expect((screen.getByPlaceholderText("Ask the demo agent...") as HTMLTextAreaElement).value).toBe("What is an AI Agent?");
  });

  it("does not overwrite user input for empty-only prefills", () => {
    renderPanel();
    fireEvent.change(screen.getByPlaceholderText("Ask the demo agent..."), { target: { value: "User typed first" } });

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: "task-tour-chat-send",
        value: "What is an AI Agent?",
        mode: "empty-only",
      });
    });

    expect((screen.getByPlaceholderText("Ask the demo agent...") as HTMLTextAreaElement).value).toBe("User typed first");
  });

  it("can expose the whole chat panel as a task-tour target", () => {
    const { container } = renderPanel("task-tour-chat-send", "task-tour-chat-window");

    expect(container.querySelector('[data-tour-id="task-tour-chat-window"]')).toBeTruthy();
  });
});
