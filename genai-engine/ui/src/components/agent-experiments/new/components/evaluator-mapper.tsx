import { Autocomplete, Divider, Paper, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { z } from "zod";

import { newAgentExperimentFormOpts } from "../form";

import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useTransform } from "@/hooks/transforms/useTransform";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { TraceTransformResponse } from "@/lib/api-client/api-client";

export const EvaluatorMapper = withForm({
  ...newAgentExperimentFormOpts,
  render: function Render({ form }) {
    const { data: transforms } = useTransforms();

    const ready = useStore(form.store, (state) => state.values.datasetRef.version && state.values.evals.length > 0);

    if (!ready) return null;

    return (
      <Stack component={Paper} variant="outlined" p={2} gap={2} divider={<Divider />}>
        <Stack gap={2}>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Map Evaluation Variables
          </Typography>
          <form.AppField name="evals" mode="array">
            {(field) => (
              <Stack gap={2}>
                {field.state.value.map((evaluator, eIndex) => (
                  <Stack
                    component={Paper}
                    variant="outlined"
                    p={2}
                    gap={2}
                    divider={<Divider />}
                    key={`${evaluator.name}-${evaluator.version}-${eIndex}`}
                  >
                    <Typography variant="body2" color="text.primary" fontWeight="bold">
                      {evaluator.name} v{evaluator.version}
                    </Typography>
                    <form.AppField name={`evals[${eIndex}].transform_id`}>
                      {(field) => {
                        const selected = transforms?.find((t) => t.id === field.state.value) ?? null;
                        return (
                          <Autocomplete
                            size="small"
                            options={transforms ?? []}
                            value={selected}
                            onChange={(_, value) => {
                              field.handleChange(value?.id ?? "");
                            }}
                            getOptionLabel={(option) => option.name}
                            renderInput={(params) => <TextField {...params} label="Transform" />}
                          />
                        );
                      }}
                    </form.AppField>
                    <EvalItem form={form} evalIndex={eIndex} />
                  </Stack>
                ))}
              </Stack>
            )}
          </form.AppField>
        </Stack>
      </Stack>
    );
  },
});

const EvalItem = withForm({
  ...newAgentExperimentFormOpts,
  props: {} as {
    evalIndex: number;
  },
  render: function Render({ form, evalIndex }) {
    const transformId = useStore(form.store, (state) => state.values.evals[evalIndex].transform_id);

    const { data: transform } = useTransform(transformId);

    if (!transform) return null;

    return (
      <Stack gap={2}>
        <form.AppField name={`evals[${evalIndex}].variable_mapping`} mode="array">
          {(field) => (
            <Stack gap={3}>
              {field.state.value.map((mapping, mIndex) => {
                const key = `evals[${evalIndex}].variable_mapping[${mIndex}]` as const;
                return (
                  <Stack key={`${mapping.variable_name}-${mIndex}`} gap={2}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="body2" color="text.primary">
                        {mapping.variable_name}
                      </Typography>
                      <form.AppField
                        name={`${key}.source.type`}
                        listeners={{
                          onChange: ({ value }) => {
                            if (value === "dataset_column") {
                              form.setFieldValue(`${key}.source`, { type: "dataset_column", dataset_column: { name: "" } });
                            } else {
                              form.setFieldValue(`${key}.source`, {
                                type: "experiment_output",
                                experiment_output: { transform_variable_name: "" },
                              });
                            }
                          },
                        }}
                      >
                        {(field) => (
                          <>
                            <ToggleButtonGroup
                              size="small"
                              value={field.state.value}
                              exclusive
                              onChange={(e, value) => {
                                field.handleChange(value);
                              }}
                            >
                              <ToggleButton value="dataset_column">Dataset Column</ToggleButton>
                              <ToggleButton value="experiment_output">Experiment Output</ToggleButton>
                            </ToggleButtonGroup>
                          </>
                        )}
                      </form.AppField>
                    </Stack>
                    <form.AppField name={`${key}.source`}>
                      {(field) => {
                        if (field.state.value.type === "dataset_column") {
                          return <EvaluatorDatasetColumnSelector form={form} evalIndex={evalIndex} mappingIndex={mIndex} />;
                        }

                        return <EvaluatorExperimentOutputSelector form={form} evalIndex={evalIndex} mappingIndex={mIndex} transform={transform} />;
                      }}
                    </form.AppField>
                  </Stack>
                );
              })}
            </Stack>
          )}
        </form.AppField>
      </Stack>
    );
  },
});

const EvaluatorDatasetColumnSelector = withForm({
  ...newAgentExperimentFormOpts,
  props: {} as {
    evalIndex: number;
    mappingIndex: number;
  },
  render: function Render({ form, evalIndex, mappingIndex }) {
    const datasetRef = useStore(form.store, (state) => state.values.datasetRef);

    const { version } = useDatasetVersionData(datasetRef.id ?? undefined, datasetRef.version ?? undefined);

    const key = `evals[${evalIndex}].variable_mapping[${mappingIndex}]` as const;

    if (!version) return null;

    return (
      <form.AppField
        name={`${key}.source.dataset_column`}
        defaultValue={{ name: "" }}
        validators={{
          onChange: z.object({ name: z.string().min(1, "Dataset column is required") }),
        }}
      >
        {(field) => {
          const selected = version.column_names.find((c) => c === field.state.value.name) ?? null;
          return (
            <Autocomplete
              size="small"
              options={version.column_names}
              getOptionLabel={(option) => option}
              value={selected}
              onChange={(_, value) => {
                field.handleChange({ name: value ?? "" });
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Dataset Column"
                  error={field.state.meta.errors.length > 0}
                  helperText={field.state.meta.errors[0]?.message}
                />
              )}
            />
          );
        }}
      </form.AppField>
    );
  },
});

const EvaluatorExperimentOutputSelector = withForm({
  ...newAgentExperimentFormOpts,
  props: {} as {
    evalIndex: number;
    mappingIndex: number;
    transform: TraceTransformResponse;
  },
  render: function Render({ form, evalIndex, mappingIndex, transform }) {
    const key = `evals[${evalIndex}].variable_mapping[${mappingIndex}]` as const;

    const variables = transform.definition.variables;

    return (
      <form.AppField name={`${key}.source.experiment_output.transform_variable_name`}>
        {(field) => {
          const selected = variables.find((v) => v.variable_name === field.state.value) ?? null;
          return (
            <Autocomplete
              size="small"
              options={variables}
              getOptionLabel={(option) => option.variable_name}
              value={selected}
              onChange={(_, value) => {
                field.handleChange(value?.variable_name ?? "");
              }}
              renderInput={(params) => <TextField {...params} label="Transform Variable" />}
            />
          );
        }}
      </form.AppField>
    );
  },
});
