import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SyntheticDataModal } from "./SyntheticDataModal";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourActions";

const syntheticSession = vi.hoisted(() => ({
  addRow: vi.fn(),
  conversation: [],
  deleteRows: vi.fn(),
  error: null,
  isLoading: false,
  reset: vi.fn(),
  rows: [],
  sendMessage: vi.fn(),
  startGeneration: vi.fn(),
  toggleLock: vi.fn(),
  updateRow: vi.fn(),
}));

vi.mock("@/features/task-tour/tourActions", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    syntheticDataFinished: "task-tour:synthetic-data-finished",
  },
}));

vi.mock("@/hooks/datasets/useSyntheticDataSession", () => ({
  useSyntheticDataSession: () => syntheticSession,
}));

vi.mock("./SyntheticDataConfigForm", () => ({
  SyntheticDataConfigForm: ({ onCancel, onSubmit }: { onCancel: () => void; onSubmit: (config: object) => void }) => (
    <div>
      <button onClick={onCancel}>Cancel synthetic generation</button>
      <button onClick={() => onSubmit({ rowCount: 5 })}>Start generation</button>
    </div>
  ),
}));

vi.mock("./SyntheticDataCanvas", () => ({
  SyntheticDataCanvas: () => <div>Canvas</div>,
}));

function renderModal(open = true) {
  return render(
    <SyntheticDataModal
      open={open}
      onClose={vi.fn()}
      columns={["question", "answer"]}
      existingRowsSample={[]}
      datasetId="dataset-id"
      versionNumber={1}
      onAcceptRows={vi.fn()}
    />
  );
}

describe("SyntheticDataModal task tour target", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("refreshes the tour target and marks the dialog surface when opened", async () => {
    renderModal();

    expect(screen.getByRole("dialog").getAttribute("data-tour-id")).toBe(TOUR_IDS.datasetGenerateSyntheticModal);
    await waitFor(() => expect(refreshTaskTourTarget).toHaveBeenCalledTimes(1));
    expect(dispatchTourEvent).not.toHaveBeenCalled();
  });

  it("completes the optional synthetic data step when the modal is canceled", () => {
    renderModal();

    fireEvent.click(screen.getByRole("button", { name: /cancel synthetic generation/i }));

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.syntheticDataFinished);
  });

  it("completes the optional synthetic data step when generation starts", async () => {
    renderModal();

    fireEvent.click(screen.getByRole("button", { name: /start generation/i }));

    await waitFor(() => expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.syntheticDataFinished));
  });
});
