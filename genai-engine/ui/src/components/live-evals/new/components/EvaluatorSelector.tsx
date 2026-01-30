import { useStore } from "@tanstack/react-form";

import { EvaluatorSelectorUI } from "./EvaluatorSelectorUI";

import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { withFieldGroup } from "@/components/traces/components/filtering/hooks/form";

type EvaluatorFormState = {
  name: string | null;
  version: string | null;
};

type EvaluatorSelectorProps = {
  taskId: string;
  onSelectionChange?: () => void;
};

export const EvaluatorSelector = withFieldGroup({
  defaultValues: {
    name: null,
    version: null,
  } as EvaluatorFormState,
  props: {} as EvaluatorSelectorProps,
  render: function Render({ group, taskId, onSelectionChange }) {
    const evaluators = useEvals(taskId, {
      page: 0,
      pageSize: 10,
      sort: "desc",
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const name = useStore(group.store, (state: any) => state.values.name as string | null);

    const versions = useEvalVersions(taskId, name ?? undefined, {
      page: 0,
      pageSize: 10,
      sort: "desc",
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const version = useStore(group.store, (state: any) => state.values.version as string | null);

    const handleNameChange = (newName: string | null) => {
      group.setFieldValue("name", newName);
      group.setFieldValue("version", null);
      onSelectionChange?.();
    };

    const handleVersionChange = (newVersion: string | null) => {
      group.setFieldValue("version", newVersion);
      onSelectionChange?.();
    };

    return (
      <EvaluatorSelectorUI
        evaluators={evaluators?.evals.map((evaluator) => evaluator.name) ?? []}
        versions={versions.versions?.map((version) => version.version.toString()) ?? []}
        selectedName={name}
        selectedVersion={version}
        onNameChange={handleNameChange}
        onVersionChange={handleVersionChange}
        isVersionsLoading={versions.isLoading}
      />
    );
  },
});
