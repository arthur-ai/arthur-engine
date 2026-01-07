import { Box, Button, Divider, Paper, Stack, TextField, Typography } from "@mui/material";

import { extractVariablesFromText } from "../hooks/useExtractVariables";

import { BodyMapper } from "./components/body-mapper";
import { DatasetSetup } from "./components/dataset";
import { EndpointSetup } from "./components/endpoint";
import { EvaluatorMapper } from "./components/evaluator-mapper";
import { EvaluatorsSelector } from "./components/evaluator-selector";
import { newAgentExperimentFormOpts } from "./form";
import { useCreateNewExperiment } from "./hooks/useCreateNewExperiment";
import { mapFormToRequest } from "./utils/mapper";

import { useAppForm, withForm } from "@/components/traces/components/filtering/hooks/form";
import { getContentHeight } from "@/constants/layout";

export const NewAgentExperiment = () => {
  const form = useAppForm({
    ...newAgentExperimentFormOpts,
    listeners: {
      onChange: ({ fieldApi, formApi }) => {
        if (!(fieldApi.name as string).startsWith("endpoint")) return;

        const endpoint = formApi.getFieldValue("endpoint");

        const bodyVariables = extractVariablesFromText(endpoint.body);
        const headersVariables = endpoint.headers
          .map((header) => [extractVariablesFromText(header.name), extractVariablesFromText(header.value)])
          .flat(2);

        const variables = Array.from(new Set([...bodyVariables, ...headersVariables]));

        formApi.setFieldValue(
          "templateVariableMapping",
          variables.map((variable) => ({
            source: {
              type: "dataset_column",
              dataset_column: { name: "" },
            },
            variable_name: variable,
          }))
        );
      },
    },
    onSubmit: async ({ value }) => {
      const request = mapFormToRequest(value);

      await newExperimentMutation.mutateAsync(request);
    },
  });

  const newExperimentMutation = useCreateNewExperiment();

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
      <Stack divider={<Divider sx={{ my: 3 }} />} p={2} overflow="auto">
        <>
          <Typography variant="h6" color="text.primary" fontWeight="bold" mb={1}>
            Endpoint Setup
          </Typography>
          <EndpointSetup form={form} />
        </>
        <>
          <Typography variant="h6" color="text.primary" fontWeight="bold" mb={1}>
            Experiment Setup
          </Typography>
          <ExperimentSetup form={form} />
        </>
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
      <Stack component={Paper} variant="outlined" p={2} gap={2} divider={<Divider />}>
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
          <DatasetSetup form={form} />
          <BodyMapper form={form} />
          <EvaluatorsSelector form={form} />
          <EvaluatorMapper form={form} />
        </Stack>
      </Stack>
    );
  },
});
