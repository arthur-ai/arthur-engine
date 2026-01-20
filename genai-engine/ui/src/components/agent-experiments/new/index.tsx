import { Box, Button, CircularProgress, Divider, Stack, TextField, Typography } from "@mui/material";
import { useSnackbar } from "notistack";
import { useRef } from "react";
import { useNavigate } from "react-router-dom";

import { extractVariablesFromText } from "../hooks/useExtractVariables";

import { BodyMapper } from "./components/body-mapper";
import { DatasetSetup } from "./components/dataset";
import { EndpointSetup } from "./components/endpoint";
import { EvaluatorMapper } from "./components/evaluator-mapper";
import { EvaluatorsSelector } from "./components/evaluator-selector";
import { RequestTimeMapper } from "./components/request-time-mapper";
import { newAgentExperimentFormOpts } from "./form";
import { useCopyFromTemplate } from "./hooks/useCopyFromTemplate";
import { useCreateNewExperiment } from "./hooks/useCreateNewExperiment";
import { mapFormToRequest, mapTemplateToRequest } from "./utils/mapper";

import { useAppForm, withForm } from "@/components/traces/components/filtering/hooks/form";
import { getContentHeight } from "@/constants/layout";
import { AgenticExperimentDetail, HttpHeader, TemplateVariableMappingInput } from "@/lib/api-client/api-client";
import { EVENT_NAMES, track } from "@/services/amplitude";

function computeVars(endpoint: { body: string; headers: HttpHeader[] }): string[] {
  const bodyVars = extractVariablesFromText(endpoint.body);

  const headerVars = endpoint.headers.flatMap((h) => [...extractVariablesFromText(h.name), ...extractVariablesFromText(h.value)]);

  return Array.from(new Set([...bodyVars, ...headerVars])).sort();
}

function varsSignature(vars: string[]) {
  return vars.join("|"); // vars already sorted
}

function rebuildMapping(vars: string[], prev: TemplateVariableMappingInput[] | undefined): TemplateVariableMappingInput[] {
  const byVar = new Map((prev ?? []).map((r) => [r.variable_name, r]));
  return vars.map((v) => byVar.get(v) ?? { variable_name: v, source: { type: "dataset_column", dataset_column: { name: "" } } });
}

export const NewAgentExperiment = () => {
  const { data: template, isLoading: isLoadingTemplate } = useCopyFromTemplate();

  if (isLoadingTemplate) {
    return <CircularProgress className="mx-auto" />;
  }

  return <Internal template={template} />;
};

const Internal = ({ template }: { template?: AgenticExperimentDetail }) => {
  const lastSignature = useRef<string | null>(null);

  const navigate = useNavigate();

  const { enqueueSnackbar } = useSnackbar();
  const form = useAppForm({
    defaultValues: mapTemplateToRequest(template),
    listeners: {
      onMount: () => {
        track(EVENT_NAMES.AGENT_EXPERIMENT_INTENT_CREATE, { template_id: template?.id });
      },
      onChange: ({ fieldApi, formApi }) => {
        const name = fieldApi.name as string;

        if (name !== "endpoint.body" && !name.startsWith("endpoint.headers")) {
          return;
        }

        const endpoint = formApi.getFieldValue("endpoint");
        const vars = computeVars(endpoint);
        const sig = varsSignature(vars);

        if (sig === lastSignature.current) return;
        lastSignature.current = sig;

        const prev = formApi.getFieldValue("templateVariableMapping") as TemplateVariableMappingInput[] | undefined;
        const next = rebuildMapping(vars, prev);

        formApi.setFieldValue("templateVariableMapping", next);
      },
    },
    onSubmit: async ({ value }) => {
      try {
        const request = mapFormToRequest(value);

        await newExperimentMutation.mutateAsync(request);
      } catch (error) {
        console.error(error);
        enqueueSnackbar("Failed to create experiment. Please check the form and try again.", { variant: "error" });
      }
    },
  });

  const newExperimentMutation = useCreateNewExperiment({
    onSuccess: (data) => {
      enqueueSnackbar(`Experiment with id "${data.id}" created successfully!`, { variant: "success" });
      navigate(`../${data.id}`, { replace: true });
    },
  });

  return (
    <Stack
      component="form"
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
      sx={{ height: getContentHeight() }}
    >
      <Box
        sx={{
          px: 3,
          pt: 3,
          pb: 2,
          borderBottom: 1,
          borderColor: "divider",
          backgroundColor: "background.paper",
        }}
      >
        <Stack>
          <Typography variant="h5" color="text.primary" fontWeight="bold" mb={0.5}>
            New Agent Experiment
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create a new agent experiment to test and optimize agent-based task execution strategies.
          </Typography>
        </Stack>
      </Box>
      <Stack p={2} overflow="auto" gap={4}>
        <Stack mb={2}>
          <Typography variant="h6" color="text.primary" fontWeight="bold">
            Endpoint Setup
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure the API endpoint that will be called during the experiment.
          </Typography>
          <Divider sx={{ my: 2 }} />
          <EndpointSetup form={form} fields={{ endpoint: "endpoint" }} />
        </Stack>
        <Stack>
          <Typography variant="h6" color="text.primary" fontWeight="bold">
            Experiment Setup
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Define the experiment parameters and select your evaluation dataset.
          </Typography>
          <Divider sx={{ my: 2 }} />
          <ExperimentSetup form={form} />
        </Stack>
      </Stack>
      <Stack direction="row" mt="auto" p={2}>
        <form.Subscribe selector={(state) => [state.canSubmit, state.isDirty, state.isSubmitting]}>
          {([canSubmit, isDirty, isSubmitting]) => (
            <Button type="submit" variant="contained" color="primary" fullWidth disabled={!canSubmit || !isDirty} loading={isSubmitting}>
              Create Experiment
            </Button>
          )}
        </form.Subscribe>
      </Stack>
    </Stack>
  );
};

export const ExperimentSetup = withForm({
  ...newAgentExperimentFormOpts,
  render: function Render({ form }) {
    return (
      <Stack gap={2}>
        <Box className="grid grid-cols-1 items-start" sx={{ gap: 2 }}>
          <Stack gap={2}>
            <form.AppField name="name">
              {(field) => (
                <TextField
                  size="small"
                  label="Experiment Name"
                  required
                  onChange={(e) => field.handleChange(e.target.value)}
                  value={field.state.value}
                />
              )}
            </form.AppField>
            <form.AppField name="description">
              {(field) => (
                <TextField
                  size="small"
                  label="Experiment Description"
                  required
                  multiline
                  minRows={2}
                  onChange={(e) => field.handleChange(e.target.value)}
                  value={field.state.value}
                />
              )}
            </form.AppField>
          </Stack>
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
          <RequestTimeMapper form={form} />
          <EvaluatorMapper form={form} fields={{ evals: "evals", datasetRef: "datasetRef" }} />
        </Box>
      </Stack>
    );
  },
});
