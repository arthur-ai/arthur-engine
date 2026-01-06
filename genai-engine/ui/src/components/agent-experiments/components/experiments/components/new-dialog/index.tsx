import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  Autocomplete,
  Box,
  Button,
  DialogActions,
  Divider,
  MenuItem,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { DialogContent, DialogTitle } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useDebouncedValue } from "@tanstack/react-pacer";
import { useEffect, useMemo, useState } from "react";

import { useAgentExperimentEndpoint } from "../../../../hooks/useAgentExperimentEndpoint";
import { useAgentExperimentsEndpoints } from "../../../../hooks/useAgentExperimentsEndpoints";

import { EvalsSelector } from "./evals-selector";
import { FormSchema, type FormValues } from "./form";

import { VariableChip } from "@/components/evaluators/VariableChip";
import { useAppForm, withFieldGroup, withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasets } from "@/hooks/useDatasets";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { useDatasetVersionHistory } from "@/hooks/useDatasetVersionHistory";
import { useTask } from "@/hooks/useTask";

const step1Fields = ["name", "dataset", "endpointId", "variableMapping", "evals"] as const;
const step1Schema = FormSchema.pick({ name: true, dataset: true, endpointId: true, variableMapping: true, evals: true });

export const NewExperimentDialogContent = () => {
  const [step, setStep] = useState<"experiment-info" | "configure-evals">("experiment-info");
  const form = useAppForm({
    defaultValues: {
      name: "",
      dataset: {
        id: null as string | null,
        version: null as number | null,
        filters: [],
      },
      endpointId: null as string | null,
      variableMapping: [],
      evals: [],
    } as FormValues,
    validators: {
      onChange: FormSchema,
    },
    onSubmit: async ({ value }) => {
      console.log(value);
    },
  });

  const step1Valid = useStore(form.store, (state) => step1Schema.safeParse(state.values).success);

  const validateFields = async (fields: readonly (keyof FormValues)[]) => {
    fields.forEach((field) => form.setFieldMeta(field, (m) => ({ ...m, isTouched: true })));

    await Promise.all(fields.map((field) => form.validateField(field, "submit")));

    return fields.every((field) => form.getFieldMeta(field)?.errors.length === 0);
  };

  const handleNext = async () => {
    const ok = await validateFields(step1Fields);

    if (!ok) return;

    setStep("configure-evals");
  };

  const handleBack = () => {
    setStep("experiment-info");
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <DialogTitle>New Experiment</DialogTitle>
      <DialogContent dividers>
        <Stepper activeStep={step === "experiment-info" ? 0 : 1} sx={{ mt: 2, mb: 4 }}>
          <Step>
            <StepLabel>Experiment Info</StepLabel>
          </Step>
          <Step>
            <StepLabel>Configure Evals</StepLabel>
          </Step>
        </Stepper>
        {step === "experiment-info" && (
          <>
            <Stack gap={2}>
              <form.Field name="name">
                {(field) => (
                  <TextField
                    size="small"
                    label="Name"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    error={field.state.meta.errors.length > 0}
                    helperText={field.state.meta.errors[0]?.message}
                  />
                )}
              </form.Field>
              <EndpointSelector form={form} fields={{ endpointId: "endpointId" }} />
              <DatasetSelector form={form} fields="dataset" />
              <EndpointDatasetMapper form={form} />
              <EvalsSelector form={form} />
            </Stack>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={() => form.reset()}>Cancel</Button>
        {step === "configure-evals" && (
          <Button onClick={handleBack} variant="contained" disableElevation>
            Back
          </Button>
        )}
        {step === "configure-evals" && (
          <Button type="submit" variant="contained" disableElevation>
            Create
          </Button>
        )}
        {step === "experiment-info" && (
          <Button onClick={handleNext} variant="contained" disableElevation disabled={!step1Valid}>
            Configure Evals
          </Button>
        )}
      </DialogActions>
    </form>
  );
};

const DatasetSelector = withFieldGroup({
  defaultValues: {} as FormValues["dataset"],
  render: function Render({ group }) {
    const [query, setQuery] = useState("");
    const { task } = useTask();

    const datasetId = useStore(group.store, (state) => state.values.id);
    const version = useStore(group.store, (state) => state.values.version);

    const [debouncedQuery] = useDebouncedValue(query, { wait: 500 });

    const { datasets, isLoading } = useDatasets(task?.id, { page: 0, pageSize: 100, sortOrder: "asc", searchQuery: debouncedQuery });

    const { versions } = useDatasetVersionHistory(datasetId ?? undefined, 0, 100);

    return (
      <Paper component={Stack} gap={2} variant="outlined" p={2}>
        <Stack>
          <Typography variant="body2" color="text.primary">
            Dataset
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Select the dataset to use for the experiment and set filters to limit the rows used in the experiment.
          </Typography>
        </Stack>
        <Stack direction="row" gap={2} width="100%">
          <group.Field
            name="id"
            listeners={{
              onChange: ({ value }) => {
                const selected = datasets?.find((d) => d.id === value);

                if (selected) {
                  group.setFieldValue("version", selected.latest_version_number ?? null);
                } else {
                  group.setFieldValue("version", null);
                }

                group.setFieldValue("filters", []);
              },
            }}
          >
            {(field) => {
              const selected = datasets?.find((d) => d.id === field.state.value);

              return (
                <Autocomplete
                  size="small"
                  fullWidth
                  loading={isLoading}
                  options={datasets ?? []}
                  value={selected ?? null}
                  inputValue={query}
                  onInputChange={(_, value) => {
                    setQuery(value);
                  }}
                  filterOptions={(x) => x}
                  onChange={(_, value) => field.handleChange(value?.id ?? "")}
                  renderInput={(params) => <TextField {...params} label="Dataset" />}
                  getOptionLabel={(option) => option.name}
                  isOptionEqualToValue={(option, value) => option.id === value.id}
                  getOptionKey={(option) => option.id}
                />
              );
            }}
          </group.Field>
          <group.Field name="version">
            {(field) => {
              const selected = versions?.find((v) => v.version_number === field.state.value);

              return (
                <Autocomplete
                  size="small"
                  disabled={!datasetId}
                  options={versions ?? []}
                  value={selected ?? null}
                  renderInput={(params) => <TextField {...params} label="Version" />}
                  onChange={(_, value) => field.handleChange(value?.version_number ?? null)}
                  getOptionLabel={(option) => `v${option.version_number}`}
                  isOptionEqualToValue={(option, value) => option.version_number === value.version_number}
                  getOptionKey={(option) => option.version_number}
                />
              );
            }}
          </group.Field>
        </Stack>
        {version && (
          <Stack gap={2} p={2} sx={{ borderColor: "divider", borderRadius: 1 }} className="border bg-blue-50">
            <Typography variant="body2" color="text.primary">
              Filter Dataset Rows (Optional).
            </Typography>
            <group.Field name="filters" mode="array">
              {(field) => {
                return (
                  <>
                    {field.state.value.map((filter, index) => (
                      <FilterConditionGroup
                        key={`${filter}-${index}`}
                        form={group}
                        fields={`filters[${index}]`}
                        datasetId={datasetId}
                        datasetVersion={version}
                        onRemove={() => field.removeValue(index)}
                      />
                    ))}
                    <Button
                      size="small"
                      variant="outlined"
                      startIcon={<AddIcon />}
                      onClick={() => {
                        field.pushValue({ column: "", value: "" });
                      }}
                    >
                      Add Filter Condition
                    </Button>
                  </>
                );
              }}
            </group.Field>
          </Stack>
        )}
      </Paper>
    );
  },
});

const EndpointSelector = withFieldGroup({
  defaultValues: {
    endpointId: "",
  },
  render: function Render({ group }) {
    const { data, isLoading } = useAgentExperimentsEndpoints();

    return (
      <>
        <group.Field name="endpointId">
          {(field) => {
            const selected = data?.find((e) => e.id === field.state.value);

            return (
              <Autocomplete
                size="small"
                loading={isLoading}
                options={data ?? []}
                value={selected ?? null}
                renderInput={(params) => <TextField {...params} label="Endpoint" />}
                onChange={(_, value) => field.handleChange(value?.id ?? "")}
                getOptionLabel={(option) => option.name}
                isOptionEqualToValue={(option, value) => option.id === value.id}
                getOptionKey={(option) => option.id}
                renderOption={(props, option, state, ownerState) => {
                  const { key, ...optionProps } = props;
                  return (
                    <Box key={key} component="li" {...optionProps} sx={[{ flexDirection: "column", alignItems: "flex-start !important" }]}>
                      <Typography variant="body1">{ownerState.getOptionLabel(option)}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {option.url}
                      </Typography>
                    </Box>
                  );
                }}
              />
            );
          }}
        </group.Field>
      </>
    );
  },
});

export const EndpointDatasetMapper = withForm({
  defaultValues: {} as FormValues,
  render: function Render({ form }) {
    const selectedEndpointId = useStore(form.store, (state) => state.values.endpointId);

    const dataset = useStore(form.store, (state) => state.values.dataset);

    const { data: endpoint } = useAgentExperimentEndpoint(selectedEndpointId);
    const { version } = useDatasetVersionData(dataset?.id ?? undefined, dataset.version ?? undefined);

    useEffect(() => {
      if (!endpoint) return;

      form.setFieldValue(
        "variableMapping",
        endpoint.variables.map((variable) => ({
          name: variable,
          source: "dataset_column",
          column: null,
        }))
      );
    }, [endpoint, form]);

    if (!version) return null;

    return (
      <Paper variant="outlined" sx={{ p: 2 }}>
        {endpoint && (
          <Stack gap={0}>
            <Typography variant="body2" color="text.primary">
              Variable Mapping
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
              Map each variable in the endpoint body and headers to a dataset column.
            </Typography>

            <form.Field name="variableMapping" mode="array">
              {(field) => {
                return (
                  <Paper component={Stack} gap={0} variant="outlined" divider={<Divider />}>
                    {field.state.value.map((variable, index) => (
                      <Stack key={`${variable}-${index}`} gap={2} p={2}>
                        <Stack direction="row" gap={1}>
                          <Typography variant="body2" color="text.secondary">
                            Variable
                          </Typography>
                          <VariableChip variable={variable.name} />
                        </Stack>
                        <VariableSourceSelector form={form} fields={`variableMapping[${index}]`} dataset={dataset} />
                      </Stack>
                    ))}
                  </Paper>
                );
              }}
            </form.Field>
          </Stack>
        )}
      </Paper>
    );
  },
});

const VariableSourceSelector = withFieldGroup({
  defaultValues: {} as FormValues["variableMapping"][number],
  props: {} as {
    dataset: FormValues["dataset"];
  },
  render: function Render({ group, dataset }) {
    const source = useStore(group.store, (state) => state.values.source);

    const { version } = useDatasetVersionData(dataset?.id ?? undefined, dataset?.version ?? undefined);

    const columns = version?.column_names ?? [];

    return (
      <Stack direction="row" gap={1} width="100%">
        <group.Field
          name="source"
          listeners={{
            onChange: () => {
              group.setFieldValue("column", null);
            },
          }}
        >
          {(field) => {
            return (
              <TextField
                select
                label="Fill from"
                size="small"
                fullWidth
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value as "dataset_column" | "request" | "per_case")}
              >
                <MenuItem value="dataset_column">Dataset Column</MenuItem>
                <MenuItem value="request">Request Time (e.g. API Token)</MenuItem>
                <MenuItem value="per_case">Per Test Case (e.g. Thread ID)</MenuItem>
              </TextField>
            );
          }}
        </group.Field>
        {source === "dataset_column" && (
          <group.Field name="column">
            {(field) => {
              return (
                <Autocomplete
                  size="small"
                  fullWidth
                  options={columns}
                  value={field.state.value}
                  renderInput={(params) => <TextField {...params} label="Column" />}
                  onChange={(_, value) => field.handleChange(value ?? "")}
                />
              );
            }}
          </group.Field>
        )}
      </Stack>
    );
  },
});

const FilterConditionGroup = withFieldGroup({
  defaultValues: {} as FormValues["dataset"]["filters"][number],
  props: {} as {
    datasetId: string | null;
    datasetVersion: number | null;
    onRemove: () => void;
  },
  render: function Render({ group, datasetId, datasetVersion, onRemove }) {
    const { version } = useDatasetVersionData(datasetId ?? undefined, datasetVersion ?? undefined);

    return (
      <Stack direction="row" gap={1} width="100%">
        <group.Field name="column">
          {(field) => {
            return (
              <Autocomplete
                size="small"
                fullWidth
                options={version?.column_names ?? []}
                value={field.state.value}
                renderInput={(params) => <TextField {...params} label="Column" required error={field.state.meta.errors.length > 0} />}
                onChange={(_, value) => field.handleChange(value ?? "")}
              />
            );
          }}
        </group.Field>
        <group.Field name="value">
          {(field) => {
            return (
              <TextField
                size="small"
                fullWidth
                label="Value"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                error={field.state.meta.errors.length > 0}
                required
              />
            );
          }}
        </group.Field>
        <Button size="small" variant="outlined" color="error" onClick={() => onRemove()}>
          <DeleteIcon fontSize="small" />
        </Button>
      </Stack>
    );
  },
});
