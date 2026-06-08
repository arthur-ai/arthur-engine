import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AddToDatasetDrawer } from "./Drawer";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourEvents";

const mutationState = vi.hoisted(() => ({
  options: null as null | {
    onSuccess?: (data: unknown, variables: { datasetId: string }) => void;
  },
}));

const formState = vi.hoisted(() => ({
  values: {
    dataset: "dataset-id",
    transform: "",
    columns: [] as { name: string; value: string }[],
  },
}));

vi.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: vi.fn() }),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("../../utils/spans", () => ({
  flattenSpans: () => [],
}));

vi.mock("@tanstack/react-form", () => ({
  useStore: (_store: unknown, selector: (state: { values: typeof formState.values }) => unknown) => selector({ values: formState.values }),
}));

vi.mock("../filtering/hooks/form", () => ({
  useAppForm: () => ({
    store: {},
    state: {
      isDirty: false,
      values: formState.values,
    },
    Field: ({
      children,
      name,
    }: {
      children: (field: { state: { value: string }; handleChange: (value: string) => void }) => ReactNode;
      name: string;
    }) =>
      children({
        state: { value: formState.values[name as keyof typeof formState.values] as string },
        handleChange: vi.fn(),
      }),
    handleSubmit: vi.fn(),
    reset: vi.fn(),
    setFieldValue: vi.fn(),
  }),
}));

vi.mock("./form/shared", () => ({
  addToDatasetFormOptions: {},
}));

vi.mock("./components/matcher", () => ({
  Matcher: () => <div>Matcher</div>,
}));

vi.mock("./components/transform-selector", () => ({
  TransformSelector: () => <div>Transform selector</div>,
}));

vi.mock("./Configurator", () => ({
  Configurator: () => <div>Configurator</div>,
}));

vi.mock("./PreviewTable", () => ({
  PreviewTable: () => <div>Preview</div>,
}));

vi.mock("./AddColumnDialog", () => ({
  AddColumnDialog: () => null,
}));

vi.mock("./CreateDatasetModal", () => ({
  CreateDatasetModal: () => null,
}));

vi.mock("./SaveTransformDialog", () => ({
  SaveTransformDialog: () => null,
}));

vi.mock("@/hooks/useApi", () => ({
  useApi: () => ({ api: {} }),
}));

vi.mock("@/hooks/useApiMutation", () => ({
  useApiMutation: (options: typeof mutationState.options) => {
    mutationState.options = options;
    return { isPending: false, mutateAsync: vi.fn() };
  },
}));

vi.mock("@/hooks/datasets/useCreateDatasetMutation", () => ({
  useCreateDatasetMutation: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useDatasetLatestVersion", () => ({
  useDatasetLatestVersion: () => ({ latestVersion: { column_names: ["input"] } }),
}));

vi.mock("@/hooks/useDatasets", () => ({
  useDatasets: () => ({
    datasets: [{ id: "dataset-id", name: "Regression Dataset" }],
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/hooks/useTask", () => ({
  useTask: () => ({ task: { id: "task-id" } }),
}));

vi.mock("@/hooks/useTrace", () => ({
  useTrace: () => ({ data: { root_spans: [] }, error: null }),
}));

vi.mock("@/hooks/transforms/useTransforms", () => ({
  useTransforms: () => ({ data: { transforms: [] }, refetch: vi.fn() }),
}));

vi.mock("@/components/transforms/hooks/useTransformVersions", () => ({
  useTransformVersions: () => ({ data: [] }),
}));

vi.mock("@/features/task-tour/tourEvents", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    traceAddedToDataset: "task-tour:trace-added-to-dataset",
  },
}));

describe("AddToDatasetDrawer task tour target", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mutationState.options = null;
  });

  it("marks the drawer surface, refreshes the target on open, and completes only after save succeeds", async () => {
    render(<AddToDatasetDrawer traceId="trace-id" open />);

    expect(screen.getByRole("presentation").querySelector(`[data-tour-id="${TOUR_IDS.traceAddToDatasetDrawer}"]`)).toBeTruthy();
    await waitFor(() => expect(refreshTaskTourTarget).toHaveBeenCalledTimes(1));
    expect(dispatchTourEvent).not.toHaveBeenCalled();

    mutationState.options?.onSuccess?.({}, { datasetId: "dataset-id" });

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.traceAddedToDataset);
  });
});
