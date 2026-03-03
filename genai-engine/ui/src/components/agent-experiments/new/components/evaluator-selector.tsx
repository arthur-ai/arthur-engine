import { useStore } from "@tanstack/react-form";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { NewAgentExperimentFormData } from "../form";

import { EvaluatorsSelectorUI } from "@arthur/shared-components";

import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { withFieldGroup } from "@arthur/shared-components";
import { useApi } from "@/hooks/useApi";
import { useTask } from "@/hooks/useTask";
import { AgenticEvalRefInput, AgenticEvalVariableMappingInput } from "@/lib/api-client/api-client";

export const EvaluatorsSelector = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "evals">,
  render: function Render({ group }) {
    const { task } = useTask();
    const { api } = useApi()!;
    const [currentEvaluator, setCurrentEvaluator] = useState<{ name: string | null; version: number | null }>({ name: null, version: null });
    const { evals } = useEvals(task?.id, { page: 0, pageSize: 100, sort: "desc" });

    const { versions } = useEvalVersions(task?.id, currentEvaluator.name ?? undefined, { page: 0, pageSize: 100, sort: "desc" });

    const addEval = useMutation({
      mutationFn: async () => {
        if (!currentEvaluator.name || !currentEvaluator.version) return;
        const response = await api.getLlmEvalApiV1TasksTaskIdLlmEvalsEvalNameVersionsEvalVersionGet(
          currentEvaluator.name,
          currentEvaluator.version.toString(),
          task!.id
        );

        return response.data;
      },
      onSuccess: (data) => {
        if (!data) return;

        const mapping =
          data.variables?.map((v) => ({ source: { type: "experiment_output" }, variable_name: v }) as AgenticEvalVariableMappingInput) ?? [];

        group.pushFieldValue("evals", { name: data.name, version: data.version ?? 1, variable_mapping: mapping, transform_id: "" });
        setCurrentEvaluator({ name: null, version: null });
      },
    });

    const selectedEvaluator = evals.find((e) => e.name === currentEvaluator.name) ?? null;
    const selectedVersion = versions.find((v) => v.version === currentEvaluator.version) ?? null;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const selectedEvals = useStore(group.store, (state: any) => state.values.evals as Array<{ name: string; version: number }>);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const fullEvals = useStore(group.store, (state: any) => state.values.evals as AgenticEvalRefInput[]);

    const currentAlreadyAdded = selectedEvals.some((e) => e.name === currentEvaluator.name && e.version === currentEvaluator.version);

    const handleAddEvaluator = async () => {
      if (!currentEvaluator.name || !currentEvaluator.version || currentAlreadyAdded) return;

      await addEval.mutateAsync();
      setCurrentEvaluator({ name: null, version: null });
    };

    const handleRemove = (index: number) => {
      const currentEvals = fullEvals.filter((_, i) => i !== index);
      group.setFieldValue("evals", currentEvals);
    };

    return (
      <EvaluatorsSelectorUI
        evaluators={evals}
        versions={versions}
        selectedEvaluator={selectedEvaluator}
        selectedVersion={selectedVersion}
        selectedEvals={selectedEvals}
        onSelectEvaluator={(evaluator) => {
          setCurrentEvaluator({ name: evaluator?.name ?? null, version: null });
        }}
        onSelectVersion={(version) => {
          setCurrentEvaluator({ name: currentEvaluator.name, version: version?.version ?? null });
        }}
        onAdd={handleAddEvaluator}
        onRemove={handleRemove}
        isAdding={addEval.isPending}
        error={currentAlreadyAdded ? "This evaluator and version have already been added!" : null}
      />
    );
  },
});
