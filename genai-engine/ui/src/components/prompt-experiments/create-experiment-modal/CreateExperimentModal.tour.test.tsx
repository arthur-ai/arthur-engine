import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { CreateExperimentModalFormValues } from "./form";

import { CreateExperimentModal } from ".";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import { dispatchTourEvent, refreshTaskTourTarget, TASK_TOUR_EVENTS } from "@/features/task-tour/tourActions";

const createMutationState = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  options: null as null | {
    onSuccess?: (data: { id: string; name: string }) => void;
  },
}));

const formState = vi.hoisted(() => ({
  values: null as null | CreateExperimentModalFormValues,
}));

function initialData(overrides: Partial<CreateExperimentModalFormValues> = {}): Partial<CreateExperimentModalFormValues> {
  return {
    info: {
      name: "Experiment",
      description: "An experiment",
      prompt: {
        name: "Prompt",
        versions: [1],
      },
      dataset: {
        id: "dataset-id",
        version: 1,
      },
      evaluators: [],
    },
    promptVariableMappings: [{ target: "input", source: "input" }],
    evalVariableMappings: [],
    ...overrides,
  };
}

function renderModal(overrides: Partial<CreateExperimentModalFormValues> = {}) {
  return render(<CreateExperimentModal open onClose={vi.fn()} initialData={initialData(overrides)} />);
}

function tourTarget(id: string) {
  return document.querySelector(`[data-tour-id="${id}"]`);
}

vi.mock("notistack", () => ({
  useSnackbar: () => ({ enqueueSnackbar: vi.fn() }),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("@tanstack/react-form", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-form")>("@tanstack/react-form");
  // `@tanstack/react-form` surfaces `formOptions` only via `export * from
  // "@tanstack/form-core"`. When this hoisted mock factory runs, form-core
  // hasn't finished evaluating yet, so the star re-export isn't enumerable and
  // spreading `actual` drops `formOptions`. Pull it from form-core directly.
  const formCore = await vi.importActual<typeof import("@tanstack/form-core")>("@tanstack/form-core");

  return {
    ...formCore,
    ...actual,
    formOptions: formCore.formOptions,
    useStore: (_store: unknown, selector: (state: { values: CreateExperimentModalFormValues }) => unknown) => selector({ values: formState.values! }),
  };
});

vi.mock("@/components/traces/components/filtering/hooks/form", async () => {
  const React = await vi.importActual<typeof import("react")>("react");

  function cloneValues(values: CreateExperimentModalFormValues): CreateExperimentModalFormValues {
    return structuredClone(values);
  }

  function pathSegments(path: string) {
    return path.replace(/\[(\d+)\]/g, ".$1").split(".");
  }

  function getFieldValue(path: string): unknown {
    return pathSegments(path).reduce<unknown>((value, segment) => {
      if (value && typeof value === "object") {
        return (value as Record<string, unknown>)[segment];
      }
      return undefined;
    }, formState.values);
  }

  function setFieldValue(path: string, nextValue: unknown) {
    const segments = pathSegments(path);
    const lastSegment = segments.at(-1);
    const target = segments.slice(0, -1).reduce<unknown>((value, segment) => {
      if (value && typeof value === "object") {
        return (value as Record<string, unknown>)[segment];
      }
      return undefined;
    }, formState.values);

    if (target && typeof target === "object" && lastSegment) {
      (target as Record<string, unknown>)[lastSegment] = nextValue;
    }
  }

  return {
    useAppForm: (options: {
      defaultValues: CreateExperimentModalFormValues;
      onSubmit?: (args: {
        value: CreateExperimentModalFormValues;
        formApi: {
          setFieldValue: (path: string, value: unknown) => void;
          reset: () => void;
        };
      }) => void | Promise<void>;
    }) => {
      const initialized = React.useRef(false);
      const [, forceRender] = React.useState(0);

      if (!initialized.current) {
        formState.values = cloneValues(options.defaultValues);
        initialized.current = true;
      }

      const rerender = () => forceRender((version) => version + 1);

      const form = {
        store: {},
        state: {
          isDirty: false,
          values: formState.values!,
        },
        AppField: ({
          children,
          name,
        }: {
          children: (field: {
            state: { value: unknown; meta: { errors: { message: string }[] } };
            handleBlur: () => void;
            handleChange: (value: unknown) => void;
          }) => React.ReactNode;
          name: string;
        }) =>
          children({
            state: { value: getFieldValue(name), meta: { errors: [] } },
            handleBlur: vi.fn(),
            handleChange: (value: unknown) => {
              setFieldValue(name, value);
              rerender();
            },
          }),
        Field: ({
          children,
          name,
        }: {
          children: (field: {
            state: { value: unknown; meta: { errors: { message: string }[] } };
            handleBlur: () => void;
            handleChange: (value: unknown) => void;
            pushValue: (value: unknown) => void;
            removeValue: (index: number) => void;
          }) => React.ReactNode;
          name: string;
        }) =>
          children({
            state: { value: getFieldValue(name), meta: { errors: [] } },
            handleBlur: vi.fn(),
            handleChange: (value: unknown) => {
              setFieldValue(name, value);
              rerender();
            },
            pushValue: vi.fn(),
            removeValue: vi.fn(),
          }),
        Subscribe: ({
          children,
          selector,
        }: {
          children: (value: unknown) => React.ReactNode;
          selector: (state: { isSubmitting: boolean; values: CreateExperimentModalFormValues }) => unknown;
        }) => children(selector({ isSubmitting: false, values: formState.values! })),
        handleSubmit: vi.fn(async () => {
          try {
            await options.onSubmit?.({
              value: formState.values!,
              formApi: {
                setFieldValue: (path: string, value: unknown) => {
                  setFieldValue(path, value);
                  rerender();
                },
                reset: vi.fn(),
              },
            });
          } catch {
            // Keep rejected mutations from escaping the test form harness.
          }
        }),
        reset: vi.fn(),
        setFieldValue: (path: string, value: unknown) => {
          setFieldValue(path, value);
          rerender();
        },
        setFieldMeta: vi.fn(),
      };

      return form;
    },
    withForm:
      (config: { props?: Record<string, unknown>; render: (props: Record<string, unknown>) => React.ReactNode }) =>
      (props: Record<string, unknown>) =>
        config.render({ ...config.props, ...props }),
  };
});

vi.mock("./components/info-step", () => ({
  InfoStep: ({ form }: { form: { handleSubmit: () => void } }) => (
    <button type="button" onClick={() => form.handleSubmit()}>
      Configure Prompts
    </button>
  ),
}));

vi.mock("@/hooks/usePromptExperiments", () => ({
  usePromptExperiment: () => ({ experiment: undefined, isLoading: false }),
  useCreateExperiment: (_taskId: string, options: { onSuccess?: (data: { id: string; name: string }) => void }) => {
    createMutationState.options = options;
    return { mutateAsync: createMutationState.mutateAsync };
  },
}));

vi.mock("@/hooks/useTask", () => ({
  useTask: () => ({ task: { id: "task-id" } }),
}));

vi.mock("@/hooks/useDatasetVersionData", () => ({
  useDatasetVersionData: () => ({ version: { column_names: ["input", "answer"] } }),
}));

vi.mock("@/features/task-tour/tourActions", () => ({
  dispatchTourEvent: vi.fn(),
  refreshTaskTourTarget: vi.fn(),
  TASK_TOUR_EVENTS: {
    createExperimentInfoCompleted: "task-tour:create-experiment-info-completed",
    createExperimentPromptMappingsCompleted: "task-tour:create-experiment-prompt-mappings-completed",
    createExperimentCreated: "task-tour:create-experiment-created",
  },
}));

describe("CreateExperimentModal task tour instrumentation", () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    formState.values = null;
    createMutationState.options = null;
    createMutationState.mutateAsync.mockResolvedValue({ id: "experiment-id", name: "Experiment" });
  });

  it("marks the dialog and active info section, refreshes the target, and does not dispatch creation on open", async () => {
    renderModal();

    expect(screen.getByRole("dialog").getAttribute("data-tour-id")).toBe(TOUR_IDS.createExperimentModal);
    expect(tourTarget(TOUR_IDS.createExperimentInfoStep)).toBeTruthy();
    await waitFor(() => expect(refreshTaskTourTarget).toHaveBeenCalledTimes(1));
    expect(dispatchTourEvent).not.toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);
  });

  it("dispatches createExperimentCreated from mutation success only", async () => {
    createMutationState.mutateAsync.mockRejectedValueOnce(new Error("create failed"));

    renderModal({ section: "prompts" });

    fireEvent.click(screen.getByRole("button", { name: /create experiment/i }));
    await waitFor(() => expect(createMutationState.mutateAsync).toHaveBeenCalledTimes(1));
    expect(dispatchTourEvent).not.toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);

    createMutationState.options?.onSuccess?.({ id: "experiment-id", name: "Experiment" });

    expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentCreated);
  });

  it("dispatches info completion and advances to prompt mappings", async () => {
    renderModal();

    fireEvent.click(screen.getByRole("button", { name: /configure prompts/i }));

    await waitFor(() => expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentInfoCompleted));
    expect(tourTarget(TOUR_IDS.createExperimentPromptMappingsStep)).toBeTruthy();
  });

  it("dispatches prompt mapping completion and advances to eval mappings when evaluators exist", async () => {
    renderModal({
      section: "prompts",
      info: {
        name: "Experiment",
        description: "An experiment",
        prompt: { name: "Prompt", versions: [1] },
        dataset: { id: "dataset-id", version: 1 },
        evaluators: [{ name: "Quality", version: 1 }],
      },
      evalVariableMappings: [{ name: "Quality", version: 1, variables: [{ name: "answer", sourceType: "dataset_column", source: "answer" }] }],
    });

    fireEvent.click(screen.getByRole("button", { name: /configure evals/i }));

    await waitFor(() => expect(dispatchTourEvent).toHaveBeenCalledWith(TASK_TOUR_EVENTS.createExperimentPromptMappingsCompleted));
    expect(tourTarget(TOUR_IDS.createExperimentEvalMappingsStep)).toBeTruthy();
  });

  it("marks final create buttons as the submit tour target", () => {
    const { unmount } = renderModal({ section: "prompts" });

    expect(screen.getByRole("button", { name: /create experiment/i }).getAttribute("data-tour-id")).toBe(TOUR_IDS.createExperimentSubmit);

    unmount();
    renderModal({
      section: "evals",
      info: {
        name: "Experiment",
        description: "An experiment",
        prompt: { name: "Prompt", versions: [1] },
        dataset: { id: "dataset-id", version: 1 },
        evaluators: [{ name: "Quality", version: 1 }],
      },
      evalVariableMappings: [{ name: "Quality", version: 1, variables: [{ name: "answer", sourceType: "dataset_column", source: "answer" }] }],
    });

    expect(screen.getByRole("button", { name: /create experiment/i }).getAttribute("data-tour-id")).toBe(TOUR_IDS.createExperimentSubmit);
  });
});
