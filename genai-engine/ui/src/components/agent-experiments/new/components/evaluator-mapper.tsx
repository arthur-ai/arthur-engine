import { withFieldGroup } from "@arthur/shared-components";
import { Autocomplete, Divider, Paper, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { z } from "zod";

import { NewAgentExperimentFormData } from "../form";

import { useTransformVersions } from "@/components/transforms/hooks/useTransformVersions";
import { useTransform } from "@/hooks/transforms/useTransform";
import { useTransforms } from "@/hooks/transforms/useTransforms";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { TraceTransformResponse } from "@/lib/api-client/api-client";

export const EvaluatorMapper = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "evals" | "datasetRef">,
  render: function Render({ group }) {
    const { data } = useTransforms();

    const transforms = data?.transforms ?? [];

    const ready = useStore(group.store, (state) => state.values.datasetRef.version && state.values.evals.length > 0);

    return (
      <Stack component={Paper} variant="outlined" p={2} sx={{ opacity: ready ? 1 : 0.5, pointerEvents: ready ? "auto" : "none" }}>
        <Stack>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Map Evaluation Variables
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Define the variables that will be used to evaluate the agent's responses.
          </Typography>
        </Stack>
        <Divider sx={{ my: 2 }} />
        {ready ? (
          <group.AppField name="evals" mode="array">
            {(field) => (
              <Stack gap={2}>
                {field.state.value.map((evaluator, eIndex) => (
                  <Stack
                    component={Paper}
                    variant="outlined"
                    p={2}
                    gap={2}
                    divider={<Divider />}
                    sx={{ backgroundColor: "var(--color-gray-50)" }}
                    key={`${evaluator.name}-${evaluator.version}-${eIndex}`}
                  >
                    <Typography variant="body2" color="text.primary" fontWeight="bold">
                      {evaluator.name} v{evaluator.version}
                    </Typography>
                    <group.AppField name={`evals[${eIndex}].transform_id`}>
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
                    </group.AppField>
                    <EvalItem
                      form={group}
                      fields={{
                        datasetRef: "datasetRef",
                        evals: "evals",
                      }}
                      evalIndex={eIndex}
                    />
                  </Stack>
                ))}
              </Stack>
            )}
          </group.AppField>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No evaluators or no dataset version selected
          </Typography>
        )}
      </Stack>
    );
  },
});

const EvalItem = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "evals" | "datasetRef">,
  props: {} as {
    evalIndex: number;
  },
  render: function Render({ group, evalIndex }) {
    const transformId = useStore(group.store, (state) => state.values.evals[evalIndex].transform_id);

    const { data: transform } = useTransform(transformId);

    if (!transform) return null;

    return (
      <Stack gap={2}>
        <group.AppField name={`evals[${evalIndex}].variable_mapping`} mode="array">
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
                      <group.AppField
                        name={`${key}.source.type`}
                        listeners={{
                          onChange: ({ value }) => {
                            group.deleteField(`${key}.source`);
                            if (value === "dataset_column") {
                              group.setFieldValue(`${key}.source`, {
                                type: "dataset_column",
                                dataset_column: { name: "" },
                              });
                            } else {
                              group.setFieldValue(`${key}.source`, {
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
                      </group.AppField>
                    </Stack>
                    <group.Subscribe selector={(state) => state.values.evals[evalIndex].variable_mapping[mIndex].source.type}>
                      {(type) => {
                        if (type === "dataset_column") {
                          return (
                            <EvaluatorDatasetColumnSelector
                              form={group}
                              fields={{ datasetRef: "datasetRef", evals: "evals" }}
                              evalIndex={evalIndex}
                              mappingIndex={mIndex}
                            />
                          );
                        }

                        return (
                          <EvaluatorExperimentOutputSelector
                            form={group}
                            fields={{ evals: "evals" }}
                            evalIndex={evalIndex}
                            mappingIndex={mIndex}
                            transform={transform}
                          />
                        );
                      }}
                    </group.Subscribe>
                  </Stack>
                );
              })}
            </Stack>
          )}
        </group.AppField>
      </Stack>
    );
  },
});

const EvaluatorDatasetColumnSelector = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "datasetRef" | "evals">,
  props: {} as {
    evalIndex: number;
    mappingIndex: number;
  },
  render: function Render({ group, evalIndex, mappingIndex }) {
    const datasetRef = useStore(group.store, (state) => state.values.datasetRef);

    const { version } = useDatasetVersionData(datasetRef.id ?? undefined, datasetRef.version ?? undefined);

    const key = `evals[${evalIndex}].variable_mapping[${mappingIndex}]` as const;

    if (!version) return null;

    return (
      <group.AppField
        name={`${key}.source.dataset_column.name`}
        validators={{
          onChange: z.string().min(1, "Dataset column is required"),
        }}
      >
        {(field) => {
          const selected = version.column_names.find((c) => c === field.state.value) ?? null;
          return (
            <Autocomplete
              size="small"
              options={version.column_names}
              getOptionLabel={(option) => option}
              value={selected}
              onChange={(_, value) => {
                field.handleChange(value ?? "");
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
      </group.AppField>
    );
  },
});

const EvaluatorExperimentOutputSelector = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "evals">,
  props: {} as {
    evalIndex: number;
    mappingIndex: number;
    transform: TraceTransformResponse;
  },
  render: function Render({ group, evalIndex, mappingIndex, transform }) {
    const key = `evals[${evalIndex}].variable_mapping[${mappingIndex}]` as const;

    const { data: versions = [] } = useTransformVersions(transform.id);
    const variables = versions[0]?.definition?.variables ?? [];

    return (
      <group.AppField
        name={`${key}.source.experiment_output.transform_variable_name`}
        validators={{
          onChange: z.string().min(1, "Transform variable is required"),
        }}
      >
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
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Transform Variable"
                  error={field.state.meta.errors.length > 0}
                  helperText={field.state.meta.errors[0]?.message}
                />
              )}
            />
          );
        }}
      </group.AppField>
    );
  },
});
