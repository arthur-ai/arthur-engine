import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "./ChatPanel";

import { dispatchTaskTourFormPrefill } from "@/features/task-tour/formPrefill";

Element.prototype.scrollIntoView = vi.fn();

afterEach(() => {
  cleanup();
});

function renderPanel(inputTourId = "task-tour-chat-send") {
  render(
    <ChatPanel
      messages={[]}
      isStreaming={false}
      activeToolCall={null}
      onSend={vi.fn()}
      onAbort={vi.fn()}
      placeholder="Ask the demo agent..."
      inputTourId={inputTourId}
    />
  );
}

describe("ChatPanel task tour prefill", () => {
  it("prefills the chat input when the matching tour form prefill is emitted", () => {
    renderPanel();

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: "task-tour-chat-send",
        value: "What are AI Agent Evals?",
      });
    });

    expect((screen.getByPlaceholderText("Ask the demo agent...") as HTMLTextAreaElement).value).toBe("What are AI Agent Evals?");
  });

  it("does not overwrite user input for empty-only prefills", () => {
    renderPanel();
    fireEvent.change(screen.getByPlaceholderText("Ask the demo agent..."), { target: { value: "User typed first" } });

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: "task-tour-chat-send",
        value: "What are AI Agent Evals?",
        mode: "empty-only",
      });
    });

    expect((screen.getByPlaceholderText("Ask the demo agent...") as HTMLTextAreaElement).value).toBe("User typed first");
  });
});
