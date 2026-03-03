import { useAppForm } from "@arthur/shared-components";
import { CircularProgress, Dialog, Stack } from "@mui/material";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { useAgenticNotebook } from "../hooks/useAgenticNotebook";
import { useAutosaveAgenticNotebook } from "../hooks/useAutosaveAgenticNotebook";
import { useExecuteAgenticNotebook } from "../hooks/useExecuteAgenticNotebook";

import { BodyVariableExtractor } from "./components/BodyVariableExtractor";
import { ExperimentConfigSelector } from "./components/experiment-config-selector";
import { Header } from "./components/header";
import { History } from "./components/history";
import { useShowState } from "./hooks/useShowState";
import { useMetaStore } from "./store/meta.store";
import { hashFormState } from "./utils/hash";
import { mapFormToCreateAgenticExperimentRequest, mapTemplateToForm } from "./utils/mapper";

import { BodyMapper } from "@/components/agent-experiments/new/components/body-mapper";
import { DatasetSetup } from "@/components/agent-experiments/new/components/dataset";
import { EndpointSetup } from "@/components/agent-experiments/new/components/endpoint";
import { EvaluatorMapper } from "@/components/agent-experiments/new/components/evaluator-mapper";
import { EvaluatorsSelector } from "@/components/agent-experiments/new/components/evaluator-selector";
import { getContentHeight } from "@/constants/layout";
import { AgenticNotebookDetail } from "@/lib/api-client/api-client";

export const AgentNotebookDetail = () => {
  const { notebookId } = useParams<{ notebookId: string }>();

  const { enqueueSnackbar } = useSnackbar();

  const { data: agenticNotebook, isLoading } = useAgenticNotebook(notebookId!);

  if (isLoading) {
    return <CircularProgress className="mx-auto" />;
  }

  if (!agenticNotebook) {
    enqueueSnackbar("Notebook not found", { variant: "error" });
    return <Navigate to=".." replace />;
  }

  return <Internal notebook={agenticNotebook} />;
};

// I think a simple Suspense would be enough here
const Internal = ({ notebook }: { notebook: AgenticNotebookDetail }) => {
  const [showExperimentConfigSelector, setShowExperimentConfigSelector] = useState(false);
  const [, setShow] = useShowState();

  const { cancel, save, forceSave, isSaving } = useAutosaveAgenticNotebook(notebook.id);
  const { execute } = useExecuteAgenticNotebook(notebook.id);

  const baseline = useMetaStore((state) => state.baselineHash);
  const actions = useMetaStore((state) => state.actions);

  const form = useAppForm({
    defaultValues: mapTemplateToForm(notebook.state),
    listeners: {
      // Autosave handler for form changes
      onChange: async ({ formApi }) => {
        const state = formApi.state.values;
        const hash = hashFormState(state);

        actions.setEdited(hash !== baseline);

        if (hash === baseline) return cancel();

        await save(state);
      },
      onChangeDebounceMs: 16,
      onMount: ({ formApi }) => {
        const state = formApi.state.values;
        const hash = hashFormState(state);

        actions.setBaseline(hash);
      },
    },
    onSubmit: async ({ value }) => {
      const id = await execute({
        ...mapFormToCreateAgenticExperimentRequest(value),
        name: `Experiment Run for notebook ${notebook.name}`,
      });

      setShow({ id, show: "history" }, { history: "push" });
    },
  });

  return (
    <>
      <Stack
        component="form"
        onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();
          form.handleSubmit();
        }}
        sx={{ height: getContentHeight() }}
      >
        <Header form={form} notebook={notebook} onLoadConfig={() => setShowExperimentConfigSelector(true)} onSave={forceSave} isSaving={isSaving} />
        <div className="flex flex-1 overflow-hidden">
          <Stack p={2} gap={2} className="flex-1 overflow-auto">
            <EndpointSetup
              form={form}
              fields={{
                endpoint: "endpoint",
              }}
            />
            <DatasetSetup
              form={form}
              fields={{
                datasetRef: "datasetRef",
                datasetRowFilter: "datasetRowFilter",
              }}
            />
            <EvaluatorsSelector form={form} fields={{ evals: "evals" }} />
            <BodyMapper
              form={form}
              fields={{
                templateVariableMapping: "templateVariableMapping",
                datasetRef: "datasetRef",
              }}
            />

            <EvaluatorMapper form={form} fields={{ datasetRef: "datasetRef", evals: "evals" }} />

            <BodyVariableExtractor form={form} />
          </Stack>
        </div>
      </Stack>

      <Dialog open={showExperimentConfigSelector} onClose={() => setShowExperimentConfigSelector(false)} fullWidth>
        <ExperimentConfigSelector form={form} onClose={() => setShowExperimentConfigSelector(false)} />
      </Dialog>

      <History notebookId={notebook.id} />
    </>
  );
};
