import { useStore } from "@tanstack/react-form";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LiveEvalsNew } from ".";

type FetchedEval = { name: string; eval_kind?: string };

const state = vi.hoisted(() => ({
  search: "",
  fetchedEval: undefined as FetchedEval | undefined,
}));

vi.mock("react-router", () => ({
  useNavigate: () => vi.fn(),
  useSearchParams: () => [new URLSearchParams(state.search)] as const,
}));

vi.mock("@arthur/shared-components", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@arthur/shared-components")>();
  return {
    ...actual,
    MustacheHighlightedTextField: ({ value }: { value: string }) => <div>{value}</div>,
  };
});

vi.mock("@/hooks/useTask", () => ({
  useTask: () => ({ task: { id: "task-1" } }),
}));

vi.mock("@/components/evaluators/hooks/useEval", () => ({
  // Mirrors the real hooks: the query is disabled unless task, name and version are all set.
  useEval: (taskId?: string, evalName?: string, evalVersion?: string) => ({
    eval: taskId && evalName && evalVersion ? state.fetchedEval : undefined,
  }),
  useMLEval: (taskId?: string, evalName?: string) => ({
    eval: taskId && evalName ? state.fetchedEval : undefined,
  }),
}));

vi.mock("../hooks/useContinuousEvalVariableMapping", () => ({
  useContinuousEvalVariableMapping: () => ({ data: undefined, isLoading: false }),
}));

vi.mock("../hooks/useCreateContinuousEval", () => ({
  useCreateContinuousEval: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("@/components/transforms/hooks/useTransforms", () => ({
  useTransforms: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
}));

vi.mock("@/components/transforms/hooks/useTransformVersions", () => ({
  useTransformVersions: () => ({ data: [], isLoading: false }),
}));

vi.mock("@/components/transforms/hooks/useCreateTransformMutation", () => ({
  useCreateTransformMutation: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

vi.mock("@/components/transforms/TransformFormModal", () => ({
  default: () => null,
}));

vi.mock("../components/variable-mapping", () => ({
  VariableMappingSection: () => null,
}));

vi.mock("./ContinuousEvalWithTracePage", () => ({
  ContinuousEvalWithTracePage: () => null,
}));

// Stands in for the real selector so the test can read the evaluator slice of form state.
vi.mock("./components/EvaluatorSelector", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  EvaluatorSelector: function EvaluatorSelectorProbe({ form }: { form: any }) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const evaluator = useStore(form.store, (formState: any) => formState.values.evaluator);
    return <div data-testid="evaluator-state">{JSON.stringify(evaluator)}</div>;
  },
}));

const readEvaluatorState = () => JSON.parse(screen.getByTestId("evaluator-state").textContent ?? "{}");

afterEach(() => {
  cleanup();
  state.search = "";
  state.fetchedEval = undefined;
});

describe("LiveEvalsNew evaluator prefill", () => {
  it("backfills eval_type from the fetched evaluator and keeps the prefilled version", () => {
    state.search = "evalName=Readability&evalVersion=3";
    state.fetchedEval = { name: "Readability", eval_kind: "llm_as_a_judge" };

    render(<LiveEvalsNew />);

    expect(readEvaluatorState()).toEqual({ name: "Readability", version: "3", eval_type: "llm_as_a_judge" });
  });

  it("backfills eval_type once the evaluator fetch resolves", () => {
    state.search = "evalName=Readability&evalVersion=3";

    const { rerender } = render(<LiveEvalsNew />);
    expect(readEvaluatorState().eval_type).toBeNull();

    state.fetchedEval = { name: "Readability", eval_kind: "llm_as_a_judge" };
    rerender(<LiveEvalsNew />);

    expect(readEvaluatorState().eval_type).toBe("llm_as_a_judge");
  });

  it("leaves an eval_type that is already set alone", () => {
    state.search = "mlEvalName=Toxicity";
    state.fetchedEval = { name: "Toxicity", eval_kind: "toxicity" };

    render(<LiveEvalsNew />);

    expect(readEvaluatorState()).toEqual({ name: "Toxicity", version: "latest", eval_type: "ml" });
  });
});

describe("LiveEvalsNew validation feedback", () => {
  it("marks an unfilled required Transform as errored once touched", () => {
    state.search = "evalName=Readability&evalVersion=3";
    state.fetchedEval = { name: "Readability", eval_kind: "llm_as_a_judge" };

    render(<LiveEvalsNew />);

    const transformInput = screen.getByLabelText("Transform");
    expect(transformInput).toHaveProperty("ariaInvalid", "false");

    fireEvent.blur(transformInput);

    expect(transformInput).toHaveProperty("ariaInvalid", "true");
  });
});
