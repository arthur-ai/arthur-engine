import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SyntheticDataModal } from "./SyntheticDataModal";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { refreshTaskTourTarget } from "@/features/task-tour/tourActions";

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
  refreshTaskTourTarget: vi.fn(),
}));

vi.mock("@/hooks/datasets/useSyntheticDataSession", () => ({
  useSyntheticDataSession: () => syntheticSession,
}));

vi.mock("./SyntheticDataConfigForm", () => ({
  SyntheticDataConfigForm: () => <div>Config form</div>,
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
  });
});
