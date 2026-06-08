import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PromptsView } from "./PromptsView";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";

const mocks = vi.hoisted(() => ({
  createExperiment: vi.fn(),
  createExperimentFromExisting: vi.fn(),
  setActiveTab: vi.fn(),
}));

vi.mock("nuqs", () => ({
  parseAsStringEnum: () => ({
    withDefault: () => ({}),
  }),
  useQueryState: () => ["prompt-experiments", mocks.setActiveTab],
}));

vi.mock("../notebooks/Notebooks", () => ({
  default: () => <div>Notebooks</div>,
}));

vi.mock("../prompts-management/PromptsManagement", () => ({
  default: () => <div>Prompts management</div>,
}));

vi.mock("../prompt-experiments/PromptExperimentsView", () => ({
  PromptExperimentsView: ({
    onRegisterCreate,
    onRegisterCreateFromExisting,
  }: {
    onRegisterCreate?: (fn: () => void) => void;
    onRegisterCreateFromExisting?: (fn: () => void) => void;
  }) => {
    onRegisterCreate?.(mocks.createExperiment);
    onRegisterCreateFromExisting?.(mocks.createExperimentFromExisting);
    return <div>Prompt experiments</div>;
  },
}));

// TOUR_IDS now resolves from the lightweight `selectors` module (no engine /
// markdown pulled in), so the barrel no longer needs mocking — only the action
// bridge is stubbed to spy on dispatch/refresh.
vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    createExperimentModalOpened: "task-tour:create-experiment-modal-opened",
    createExperimentCreated: "task-tour:create-experiment-created",
  },
}));

describe("PromptsView create experiment tour action", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("refreshes the tour target when the Experiment menu opens", async () => {
    render(<PromptsView />);

    fireEvent.click(screen.getByRole("button", { name: /experiment/i }));

    await waitFor(() => expect(refreshTaskTourTarget).toHaveBeenCalledOnce());
    expect(screen.getByRole("menuitem", { name: /create new/i }).getAttribute("data-tour-id")).toBe(TOUR_IDS.promptsExperimentCreateNew);
  });

  it("dispatches modal opened, not final completion, when Create New is selected", () => {
    render(<PromptsView />);

    fireEvent.click(screen.getByRole("button", { name: /experiment/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /create new/i }));

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentModalOpened);
    expect(dispatchTourEvent).not.toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);
    expect(mocks.createExperiment).toHaveBeenCalledOnce();
  });
});
