import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PromptDetailView from "./PromptDetailView";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";

const navigate = vi.hoisted(() => vi.fn());
const api = vi.hoisted(() => ({
  listNotebooksApiV1TasksTaskIdNotebooksGet: vi.fn(),
  getNotebookStateApiV1NotebooksNotebookIdStateGet: vi.fn(),
}));
const notebookMutations = vi.hoisted(() => ({
  createNotebook: vi.fn(),
  setNotebookState: vi.fn(),
}));
const promptTagMutation = vi.hoisted(() => vi.fn());

vi.mock("@arthur/shared-components", () => ({
  MustacheHighlightedTextField: ({ value }: { value: string }) => <textarea readOnly value={value} />,
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
}));

vi.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: vi.fn() }),
}));

vi.mock("../hooks/useAddTagToPromptVersionMutation", () => ({
  useAddTagToPromptVersionMutation: () => ({ isPending: false, mutateAsync: promptTagMutation }),
}));

vi.mock("../hooks/useDeleteTagFromPromptVersionMutation", () => ({
  useDeleteTagFromPromptVersionMutation: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/contexts/DisplaySettingsContext", () => ({
  useDisplaySettings: () => ({ timezone: "UTC", use24Hour: true }),
}));

vi.mock("@/hooks/useApi", () => ({
  useApi: () => ({ api }),
}));

vi.mock("@/hooks/useNotebooks", () => ({
  useCreateNotebookMutation: () => ({ isPending: false, mutateAsync: notebookMutations.createNotebook }),
  useSetNotebookStateMutation: () => ({ isPending: false, mutateAsync: notebookMutations.setNotebookState }),
}));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  TASK_TOUR_EVENTS: {
    promptOpenedInPlayground: "task-tour:prompt-opened-in-playground",
    promptPromoted: "task-tour:prompt-promoted",
  },
}));

const promptData = {
  model_provider: "OpenAI",
  model_name: "gpt-4o",
  created_at: "2026-01-01T00:00:00Z",
  deleted_at: null,
  config: null,
  tags: [],
  messages: [{ role: "system", content: "Be readable." }],
};

describe("PromptDetailView playground task tour event", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    api.listNotebooksApiV1TasksTaskIdNotebooksGet.mockResolvedValue({ data: { data: [] } });
    api.getNotebookStateApiV1NotebooksNotebookIdStateGet.mockResolvedValue({ data: { prompt_configs: [] } });
    notebookMutations.createNotebook.mockResolvedValue({ id: "notebook-id" });
    notebookMutations.setNotebookState.mockResolvedValue({});
    promptTagMutation.mockResolvedValue({});
  });

  it("marks Open in Playground and dispatches after navigation succeeds", async () => {
    render(
      <PromptDetailView
        promptData={promptData as never}
        isLoading={false}
        error={null}
        promptName="Support Agent"
        version={2}
        latestVersion={2}
        taskId="task-id"
      />
    );

    const button = screen.getByRole("button", { name: /open in playground/i });
    expect(button.getAttribute("data-tour-id")).toBe(TOUR_IDS.promptOpenInPlayground);

    fireEvent.click(button);

    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith("/tasks/task-id/playgrounds/prompts?notebookId=notebook-id&promptName=Support%20Agent&version=2")
    );
    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.promptOpenedInPlayground);
  });

  it("marks Prompt Tags as the tour popover target and completes when cancelled", async () => {
    render(
      <PromptDetailView
        promptData={promptData as never}
        isLoading={false}
        error={null}
        promptName="Support Agent"
        version={2}
        latestVersion={2}
        taskId="task-id"
      />
    );
    vi.clearAllMocks();

    fireEvent.click(screen.getByRole("button", { name: /add tag/i }));

    const popover = await screen.findByText("Prompt Tags");
    expect(popover.closest(`[data-tour-id="${TOUR_IDS.promptTagsPopover}"]`)).toBeTruthy();
    expect(dispatchTourEvent).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.promptPromoted);
  });

  it("completes prompt versioning tour step after saving any tag", async () => {
    render(
      <PromptDetailView
        promptData={promptData as never}
        isLoading={false}
        error={null}
        promptName="Support Agent"
        version={2}
        latestVersion={2}
        taskId="task-id"
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /add tag/i }));
    fireEvent.change(await screen.findByLabelText(/tag name/i), { target: { value: "candidate" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() => expect(promptTagMutation).toHaveBeenCalledWith(expect.objectContaining({ data: { tag: "candidate" } })));
    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.promptPromoted);
  });
});
