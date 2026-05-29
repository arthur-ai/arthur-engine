import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SyntheticDataConfigForm } from "./SyntheticDataConfigForm";

import { dispatchTaskTourFormPrefill } from "@/features/task-tour/formPrefill";
import { TOUR_IDS } from "@/features/task-tour/selectors";

const useApiQueryMock = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/useApiQuery", () => ({
  useApiQuery: useApiQueryMock,
}));

const SYNTHETIC_DATA_PREFILL_TEXT = "Data for testing general-purpose wikipedia search agent";

function renderForm() {
  return render(
    <SyntheticDataConfigForm columns={["query", "response"]} existingRowsSample={[]} onSubmit={vi.fn()} onCancel={vi.fn()} isLoading={false} />
  );
}

function datasetPurposeInput(): HTMLTextAreaElement {
  return screen.getByLabelText(/dataset purpose/i) as HTMLTextAreaElement;
}

function columnDescriptionInput(columnName: string): HTMLInputElement {
  return screen.getByLabelText(new RegExp(`^${columnName}`, "i")) as HTMLInputElement;
}

describe("SyntheticDataConfigForm task tour prefill", () => {
  beforeEach(() => {
    useApiQueryMock.mockImplementation(({ method }: { method: string }) => {
      if (method === "getSyntheticDataPromptStatusApiV2DatasetsSyntheticDataPromptStatusGet") {
        return {
          data: {
            is_placeholder: false,
            model_name: "gpt-4o-mini",
            model_provider: "openai",
          },
          isLoading: false,
        };
      }

      return { data: undefined, isLoading: false };
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("prefills the dataset purpose when the synthetic data tour prefill is emitted", () => {
    renderForm();

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: TOUR_IDS.datasetGenerateSyntheticModal,
        values: {
          datasetPurpose: SYNTHETIC_DATA_PREFILL_TEXT,
          columnDescriptions: {
            query: "A general-purpose question for the Wikipedia search agent to answer.",
            response: "The expected answer from the Wikipedia search agent.",
          },
        },
        mode: "empty-only",
      });
    });

    expect(datasetPurposeInput().value).toBe(SYNTHETIC_DATA_PREFILL_TEXT);
    expect(columnDescriptionInput("query").value).toBe("A general-purpose question for the Wikipedia search agent to answer.");
    expect(columnDescriptionInput("response").value).toBe("The expected answer from the Wikipedia search agent.");
  });

  it("does not overwrite user-entered values in empty-only mode", () => {
    renderForm();
    fireEvent.change(datasetPurposeInput(), { target: { value: "User typed purpose" } });
    fireEvent.change(columnDescriptionInput("query"), { target: { value: "User typed query description" } });

    act(() => {
      dispatchTaskTourFormPrefill({
        targetId: TOUR_IDS.datasetGenerateSyntheticModal,
        values: {
          datasetPurpose: SYNTHETIC_DATA_PREFILL_TEXT,
          columnDescriptions: {
            query: "A general-purpose question for the Wikipedia search agent to answer.",
            response: "The expected answer from the Wikipedia search agent.",
          },
        },
        mode: "empty-only",
      });
    });

    expect(datasetPurposeInput().value).toBe("User typed purpose");
    expect(columnDescriptionInput("query").value).toBe("User typed query description");
    expect(columnDescriptionInput("response").value).toBe("The expected answer from the Wikipedia search agent.");
  });
});
