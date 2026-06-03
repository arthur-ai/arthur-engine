import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PlaygroundHeader from "./PlaygroundHeader";

import { dispatchTourEvent } from "@/features/task-tour/tourEvents";

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("./VariableInputs", () => ({
  default: () => <div>Variables</div>,
}));

vi.mock("@/components/common", () => ({
  EditableTitle: ({ value }: { value: string }) => <span>{value}</span>,
}));

vi.mock("@/hooks/useTask", () => ({
  useTask: () => ({ task: { id: "task-id" } }),
}));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  TASK_TOUR_EVENTS: {
    playgroundPromptsCreated: "task-tour:playground-prompts-created",
  },
}));

function renderHeader(onAddPrompt = vi.fn()) {
  render(
    <PlaygroundHeader
      notebookId="notebook-id"
      saveStatus="saved"
      notebookName="Notebook"
      onSaveRename={vi.fn()}
      isRenamePending={false}
      onManualSave={vi.fn()}
      configDrawerOpen={false}
      configModeActive={false}
      experimentConfig={null}
      onToggleConfigDrawer={vi.fn()}
      blankVariablesCount={0}
      onAddPrompt={onAddPrompt}
      runAllDisabledReason={null}
      onRunAllPrompts={vi.fn()}
    />
  );
}

describe("PlaygroundHeader task tour events", () => {
  it("does not complete the drafting tour step when Add Prompt is clicked", () => {
    const onAddPrompt = vi.fn();
    renderHeader(onAddPrompt);

    fireEvent.click(screen.getByRole("button", { name: /add prompt/i }));

    expect(onAddPrompt).toHaveBeenCalledTimes(1);
    expect(dispatchTourEvent).not.toHaveBeenCalled();
  });
});
