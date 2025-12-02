import AddIcon from "@mui/icons-material/Add";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import {
  Autocomplete,
  Box,
  Button,
  Checkbox,
  Chip,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  Paper,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect, useMemo } from "react";
import z from "zod";

import { useEval } from "@/components/evaluators/hooks/useEval";
import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import NunjucksHighlightedTextField from "@/components/evaluators/MustacheHighlightedTextField";
import { VariableChip } from "@/components/evaluators/VariableChip";
import { useAppForm, withFieldGroup } from "@/components/traces/components/filtering/hooks/form";
import { useTransforms } from "@/components/transforms/hooks/useTransforms";
import { TraceTransform } from "@/components/transforms/types";
import { getContentHeight } from "@/constants/layout";
import { useDatasets } from "@/hooks/useDatasets";
import { useTask } from "@/hooks/useTask";

type Evaluator = {
  name: string | null;
  version: string | null;
  variables: Record<string, boolean>;
};

type Transform = {
  datasetId: string | null;
  transformId: string | null;
};

type VariableMappings = Record<string, string | null>;

export const LiveEvalsNew = () => {
  const { task } = useTask();
  const { spacing } = useTheme();

  const form = useAppForm({
    defaultValues: {
      evaluator: {
        name: null,
        version: null,
      } as Evaluator,
      transform: {
        datasetId: null,
        transformId: null,
      } as Transform,
      mappings: {} as VariableMappings,
    },
    validators: {
      onChange: z.object({
        evaluator: z.object({
          name: z.string().min(1, "Evaluator name is required"),
          version: z.string().min(1, "Evaluator version is required"),
          variables: z.record(z.string(), z.boolean()),
        }),
        transform: z.object({
          datasetId: z.string().min(1, "Dataset ID is required"),
          transformId: z.string().min(1, "Transform ID is required"),
        }),
        mappings: z.record(z.string(), z.string().nullable()),
      }),
    },
  });

  const evaluator = useStore(form.store, (state) => state.values.evaluator);
  const transform = useStore(form.store, (state) => state.values.transform);

  const { eval: evaluatorData } = useEval(task?.id, evaluator.name ?? undefined, evaluator.version ?? undefined);
  const transforms = useTransforms(task?.id ?? undefined);

  const selectedTransform = useMemo(() => transforms.data?.find((t) => t.id === transform.transformId), [transforms.data, transform.transformId]);

  // Initialize variables when evaluator data loads
  useEffect(() => {
    if (evaluatorData) {
      const variables =
        evaluatorData.variables?.reduce(
          (acc, variable) => {
            acc[variable] = true;
            return acc;
          },
          {} as Record<string, boolean>
        ) ?? {};
      form.setFieldValue("evaluator.variables", variables);
    }
  }, [evaluatorData, form]);

  // Initialize mappings when evaluator variables change
  useEffect(() => {
    if (evaluatorData?.variables) {
      const currentMappings = form.getFieldValue("mappings");
      const newMappings: VariableMappings = {};

      evaluatorData.variables.forEach((variable) => {
        newMappings[variable] = currentMappings[variable] ?? null;
      });

      form.setFieldValue("mappings", newMappings);
    }
  }, [evaluatorData?.variables, form]);

  // All variables from the evaluator
  const allVariables = useMemo(() => {
    return Object.keys(evaluator.variables ?? {});
  }, [evaluator.variables]);

  const showMappingEditor = allVariables.length > 0 && selectedTransform;

  return (
    <Stack sx={{ height: getContentHeight() }}>
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
            New Live Eval
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create a new live eval to monitor and analyze your model's performance in real-time.
          </Typography>
        </Stack>
      </Box>
      <Stack sx={{ p: 3, width: "100%", flex: 1, overflow: "auto" }} gap={2}>
        <EvaluatorSelector taskId={task?.id ?? ""} form={form} fields="evaluator" />

        {evaluatorData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 items-start" style={{ gap: spacing(2) }}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <NunjucksHighlightedTextField value={evaluatorData?.instructions ?? ""} onChange={() => {}} readOnly size="small" />
            </Paper>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="body1" color="text.primary" fontWeight="bold">
                Variable Requirements
              </Typography>
              <FormControl component="fieldset" variant="standard">
                <FormLabel component="legend">Mark as required (eval won't run if missing)</FormLabel>
                <FormGroup>
                  {Object.entries(evaluator.variables ?? {}).map(([variable]) => (
                    <form.AppField
                      key={variable}
                      name={`evaluator.variables.${variable}`}
                      children={(field) => (
                        <FormControlLabel
                          control={
                            <Checkbox size="small" checked={field.state.value} onChange={(event) => field.handleChange(event.target.checked)} />
                          }
                          label={<VariableChip variable={variable} />}
                        />
                      )}
                    />
                  ))}
                </FormGroup>
              </FormControl>
            </Paper>
          </div>
        )}

        <TransformSelector taskId={task?.id ?? ""} form={form} fields="transform" />

        {showMappingEditor && <VariableMappingEditor variables={allVariables} transform={selectedTransform} form={form} fields="mappings" />}
      </Stack>

      <Box sx={{ p: 3, borderTop: 1, borderColor: "divider" }} className="mt-auto w-full">
        <form.Subscribe selector={(state) => [state.canSubmit, state.isDirty]}>
          {([canSubmit, isDirty]) => (
            <Button variant="contained" size="large" color="primary" disabled={!canSubmit || !isDirty} fullWidth>
              Create Live Eval
            </Button>
          )}
        </form.Subscribe>
      </Box>
    </Stack>
  );
};

const EvaluatorSelector = withFieldGroup({
  defaultValues: {
    name: null,
    version: null,
  } as Evaluator,
  props: {} as {
    taskId: string;
  },
  render: function Render({ group, taskId }) {
    const evaluators = useEvals(taskId, {
      page: 0,
      pageSize: 10,
      sort: "desc",
    });

    const name = useStore(group.store, (state) => state.values.name);

    const versions = useEvalVersions(taskId, name ?? undefined, {
      page: 0,
      pageSize: 10,
      sort: "desc",
    });

    return (
      <Stack gap={2}>
        <Typography variant="h6" color="text.primary" fontWeight="bold">
          Select an evaluator and a version
        </Typography>
        <Stack direction="row" gap={2} width="100%">
          <group.AppField
            name="name"
            listeners={{
              onChange: () => {
                group.setFieldValue("version", null);
              },
            }}
            children={(field) => (
              <field.MaterialAutocompleteField
                sx={{ flex: 1 }}
                options={evaluators?.evals.map((evaluator) => evaluator.name)}
                renderInput={(params) => <TextField {...params} label="Evaluator" />}
              />
            )}
          />

          <group.AppField
            name="version"
            children={(field) => (
              <field.MaterialAutocompleteField
                multiple={false}
                onBlur={() => {
                  field.handleBlur();
                }}
                sx={{ width: 200 }}
                loading={versions.isLoading}
                disabled={!name}
                options={versions.versions?.map((version) => version.version.toString())}
                getOptionLabel={(option) => `v${option}`}
                renderInput={(params) => <TextField {...params} label="Version" />}
              />
            )}
          />
        </Stack>
      </Stack>
    );
  },
});

const TransformSelector = withFieldGroup({
  defaultValues: {
    datasetId: null,
    transformId: null,
  } as Transform,
  props: {} as {
    taskId: string;
  },
  render: function Render({ group, taskId }) {
    const [datasetId] = useStore(group.store, ({ values }) => [values.datasetId]);

    const datasets = useDatasets(taskId, { page: 0, pageSize: 10, sortOrder: "desc" });
    const transforms = useTransforms(datasetId ?? undefined);

    return (
      <Stack gap={2}>
        <Stack direction="row" gap={2} width="100%" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" color="text.primary" fontWeight="bold">
            Select a transform
          </Typography>
          <Button variant="contained" size="small" color="primary" startIcon={<AddIcon />} onClick={() => {}}>
            Create New Transform
          </Button>
        </Stack>
        <Stack direction="row" gap={2} width="100%">
          <group.AppField
            name="datasetId"
            listeners={{
              onChange: () => {
                group.setFieldValue("transformId", null);
              },
            }}
            children={(field) => {
              const selected = datasets.datasets.find((dataset) => dataset.id === field.state.value);

              return (
                <Autocomplete
                  sx={{ flex: 1 }}
                  value={selected}
                  loading={datasets.isLoading}
                  options={datasets.datasets}
                  onChange={(_, value) => {
                    field.handleChange(value?.id ?? "");
                  }}
                  getOptionLabel={(option) => option.name}
                  isOptionEqualToValue={(option, value) => option.id === value.id}
                  getOptionKey={(option) => option.id}
                  renderInput={(params) => <TextField {...params} label="Dataset" />}
                />
              );
            }}
          />

          <group.AppField
            name="transformId"
            children={(field) => {
              const selected = transforms.data?.find((transform) => transform.id === field.state.value);

              return (
                <Autocomplete
                  sx={{ flex: 1 }}
                  loading={transforms.isLoading}
                  options={transforms.data ?? []}
                  multiple={false}
                  value={selected}
                  onChange={(_, value) => {
                    field.handleChange(value?.id ?? "");
                  }}
                  getOptionLabel={(option) => option.name}
                  isOptionEqualToValue={(option, value) => option.id === value.id}
                  getOptionKey={(option) => option.id}
                  disabled={!datasetId}
                  renderInput={(params) => <TextField {...params} label="Transform" />}
                />
              );
            }}
          />
        </Stack>
      </Stack>
    );
  },
});

const VariableMappingEditor = withFieldGroup({
  defaultValues: {} as VariableMappings,
  props: {} as {
    variables: string[];
    transform: TraceTransform;
  },
  render: function Render({ group, variables, transform }) {
    const mappings = useStore(group.store, (state) => state.values);
    const transformColumns = transform.definition.variables;

    const mappedCount = Object.entries(mappings).filter(([key, value]) => variables.includes(key) && value !== null && value !== "").length;

    return (
      <Stack gap={2}>
        <Stack direction="row" gap={2} alignItems="center" justifyContent="space-between">
          <Typography variant="h6" color="text.primary" fontWeight="bold">
            Map variables to columns
          </Typography>
          <Chip
            label={`${mappedCount}/${variables.length} mapped`}
            size="small"
            color={mappedCount === variables.length ? "success" : "default"}
            variant="outlined"
          />
        </Stack>

        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Stack divider={<Box sx={{ borderBottom: 1, borderColor: "divider" }} />}>
            {variables.map((variable) => (
              <group.AppField
                key={variable}
                name={variable}
                validators={{
                  onChange: z.string().min(1, "Column is required"),
                }}
                children={(field) => {
                  const selectedColumn = transformColumns.find((col) => col.variable_name === field.state.value);

                  return (
                    <Stack
                      direction="row"
                      alignItems="center"
                      gap={2}
                      sx={{
                        px: 2,
                        py: 1.5,
                        "&:hover": { backgroundColor: "action.hover" },
                      }}
                    >
                      <VariableChip variable={variable} sx={{ minWidth: 120 }} />

                      <ArrowForwardIcon sx={{ color: "text.disabled", fontSize: 18 }} />

                      <Autocomplete
                        size="small"
                        sx={{ flex: 1, maxWidth: 300 }}
                        value={selectedColumn ?? null}
                        options={transformColumns}
                        onChange={(_, value) => {
                          field.handleChange(value?.variable_name ?? null);
                        }}
                        getOptionLabel={(option) => option.variable_name}
                        isOptionEqualToValue={(option, value) => option.variable_name === value.variable_name}
                        renderInput={(params) => <TextField {...params} placeholder="Select column..." size="small" />}
                        renderOption={(props, option) => {
                          const { key, ...rest } = props;
                          return (
                            <li key={key} {...rest}>
                              <Stack>
                                <Typography variant="body2" fontWeight={500}>
                                  {option.variable_name}
                                </Typography>
                                <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace" }}>
                                  {option.span_name}.{option.attribute_path}
                                </Typography>
                              </Stack>
                            </li>
                          );
                        }}
                      />

                      {selectedColumn && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontFamily: "monospace", flexShrink: 0 }}>
                          {selectedColumn.span_name}.{selectedColumn.attribute_path}
                        </Typography>
                      )}
                    </Stack>
                  );
                }}
              />
            ))}
          </Stack>
        </Paper>

        {mappedCount < variables.length && (
          <Typography variant="caption" color="warning.main">
            All variables must be mapped before creating the live eval
          </Typography>
        )}
      </Stack>
    );
  },
});
