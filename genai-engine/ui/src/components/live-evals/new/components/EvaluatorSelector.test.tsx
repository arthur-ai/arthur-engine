import { useAppForm } from "@arthur/shared-components";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import z from "zod";

import { EvaluatorSelector } from "./EvaluatorSelector";

vi.mock("@/components/evaluators/hooks/useEvals", () => ({
  useEvals: () => ({
    evals: [{ name: "Readability", eval_kind: "llm_as_a_judge", versions: 3 }],
    count: 1,
    isLoading: false,
    refetch: vi.fn(),
  }),
}));

vi.mock("@/components/evaluators/hooks/useEvalVersions", () => ({
  useEvalVersions: () => ({ versions: [{ version: 3 }], count: 1, isLoading: false, refetch: vi.fn() }),
}));

vi.mock("@/components/evaluators/hooks/useCreateEvalMutation", () => ({
  useCreateEvalMutation: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

vi.mock("@/components/ml-evaluators/hooks/useCreateMlEvalMutation", () => ({
  useCreateMlEvalMutation: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

vi.mock("@/hooks/useApiQuery", () => ({
  useApiQuery: () => ({ data: undefined, isLoading: false }),
}));

vi.mock("@/components/evaluators/CreateEvalTypeModal", () => ({ default: () => null }));
vi.mock("@/components/evaluators/EvalFormModal", () => ({ default: () => null }));
vi.mock("@/components/ml-evaluators/MLEvalFormModal", () => ({ default: () => null }));

type Evaluator = { name: string | null; version: string | null; eval_type: string | null };

// Mirrors the evaluator slice of the New Continuous Eval form, validators included.
const schema = z.object({
  evaluator: z.object({
    name: z.string().min(1, "Evaluator name is required"),
    version: z.string().min(1, "Evaluator version is required"),
    eval_type: z.string().min(1, "Evaluator type is required"),
  }),
});

function Harness({ evaluator }: { evaluator: Evaluator }) {
  const form = useAppForm({ defaultValues: { evaluator }, validators: { onMount: schema, onChange: schema } });
  return <EvaluatorSelector taskId="task-1" form={form} fields="evaluator" />;
}

afterEach(() => {
  cleanup();
});

describe("EvaluatorSelector", () => {
  it("renders a prefilled evaluator and version", () => {
    render(<Harness evaluator={{ name: "Readability", version: "3", eval_type: null }} />);

    expect(screen.getByLabelText("Evaluator")).toHaveProperty("value", "Readability");
    expect(screen.getByLabelText("Version")).toHaveProperty("value", "3");
  });

  it("marks an unfilled required evaluator as errored once touched", () => {
    render(<Harness evaluator={{ name: null, version: null, eval_type: null }} />);

    const evaluatorInput = screen.getByLabelText("Evaluator");
    expect(evaluatorInput).toHaveProperty("ariaInvalid", "false");

    fireEvent.blur(evaluatorInput);

    expect(evaluatorInput).toHaveProperty("ariaInvalid", "true");
  });
});
