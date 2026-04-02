import { EvaluatorSelectorUI } from "@arthur/shared-components";
import { withFieldGroup } from "@arthur/shared-components";
import { useStore } from "@tanstack/react-form";
import { useEffect, useState } from "react";

import EvalFormModal from "@/components/evaluators/EvalFormModal";
import { useCreateEvalMutation } from "@/components/evaluators/hooks/useCreateEvalMutation";
import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";

type EvaluatorFormState = {
  name: string | null;
  version: string | null;
};

type EvaluatorSelectorProps = {
  taskId: string;
  onSelectionChange?: () => void;
};

function useDebouncedValue(value: string, delayMs: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export const EvaluatorSelector = withFieldGroup({
  defaultValues: {
    name: null,
    version: null,
  } as EvaluatorFormState,
  props: {} as EvaluatorSelectorProps,
  render: function Render({ group, taskId, onSelectionChange }) {
    const [openCreateEvalModal, setOpenCreateEvalModal] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");
    const debouncedSearch = useDebouncedValue(searchTerm, 300);

    const evaluators = useEvals(taskId, {
      page: 0,
      pageSize: 30,
      sort: "desc",
      llm_asset_names: debouncedSearch ? [debouncedSearch] : null,
    });

    const createEval = useCreateEvalMutation(taskId, async (evalData) => {
      await evaluators.refetch();
      setOpenCreateEvalModal(false);
      group.setFieldValue("name", evalData.name);
      group.setFieldValue("version", evalData.version?.toString() ?? null);
      onSelectionChange?.();
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const name = useStore(group.store, (state: any) => state.values.name as string | null);

    const versions = useEvalVersions(taskId, name ?? undefined, {
      page: 0,
      pageSize: 100,
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
      <>
        <EvaluatorSelectorUI
          evaluators={evaluators?.evals.map((evaluator) => evaluator.name) ?? []}
          versions={versions.versions?.map((version) => version.version.toString()) ?? []}
          selectedName={name}
          selectedVersion={version}
          onNameChange={handleNameChange}
          onVersionChange={handleVersionChange}
          isVersionsLoading={versions.isLoading}
          // TODO: EvaluatorSelectorUI in @arthur/shared-components does not declare
          // isEvaluatorsLoading or onSearchChange in EvaluatorSelectorUIProps — these
          // props cause a TS2322 type error. Remove once the shared-components package
          // is updated to include them, or remove them if they are no longer needed.
          // @ts-expect-error isEvaluatorsLoading not yet in EvaluatorSelectorUIProps
          isEvaluatorsLoading={evaluators.isLoading}
          onCreateNew={() => setOpenCreateEvalModal(true)}
          isCreateLoading={createEval.isPending}
          // @ts-expect-error onSearchChange not yet in EvaluatorSelectorUIProps
          onSearchChange={setSearchTerm}
        />
        <EvalFormModal
          open={openCreateEvalModal}
          onClose={() => setOpenCreateEvalModal(false)}
          onSubmit={async (evalName, data) => {
            await createEval.mutateAsync({ evalName, data });
          }}
          isLoading={createEval.isPending}
        />
      </>
    );
  },
});
