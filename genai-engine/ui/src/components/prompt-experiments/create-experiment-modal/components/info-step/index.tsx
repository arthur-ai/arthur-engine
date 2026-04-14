import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { Autocomplete, Box, Button, Chip, DialogActions, DialogContent, IconButton, Stack, TextField, Tooltip, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useEffect, useState } from "react";

import { createExperimentModalFormOpts, CreateExperimentModalFormValues } from "../../form";
import { useGetEvalVariables } from "../../hooks/useGetEvalVariables";
import { useGetPromptsVariables } from "../../hooks/useGetPromptsVariables";

import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { usePrompts } from "@/components/prompts-management/hooks/usePrompts";
import { usePromptVersions } from "@/components/prompts-management/hooks/usePromptVersions";
import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasets } from "@/hooks/useDatasets";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { useDatasetVersionHistory } from "@/hooks/useDatasetVersionHistory";
import { useTask } from "@/hooks/useTask";

export const InfoStep = withForm({
  ...createExperimentModalFormOpts,
  props: {
    onCancel: () => {},
  },
  render: function Render({ form, onCancel }) {
    const promptsVariables = useGetPromptsVariables();
    const evalsVariables = useGetEvalVariables();

    const dataset = useStore(form.store, (state) => state.values.info.dataset);
    const versionQuery = useDatasetVersionData(dataset.id ?? undefined, dataset.version ?? undefined);

    const handleSubmit = async () => {
      const state = form.state.values;

      const { prompt, evaluators } = state.info;

      const [promptVariables, evalVariables] = await Promise.all([
        promptsVariables.getVariables({ name: prompt.name, versions: prompt.versions }),
        evalsVariables.getVariables(evaluators.filter((e) => e.version !== null).map((e) => ({ name: e.name, version: e.version! }))),
      ]);

      const columnNames = versionQuery.version?.column_names ?? [];

      if (state.promptVariableMappings.length === 0) {
        form.setFieldValue(
          "promptVariableMappings",
          promptVariables.map((variable) => ({
            target: variable,
            source: columnNames.find((col) => col === variable) ?? "",
          }))
        );
      }

      if (state.evalVariableMappings.length === 0) {
        form.setFieldValue(
          "evalVariableMappings",
          evalVariables.map(({ name, version, variables }) => ({
            name,
            version: version ?? 1,
            variables: variables.map((variable) => ({
              name: variable!,
              sourceType: "dataset_column",
              source: columnNames.find((col) => col === variable) ?? "",
            })),
          }))
        );
      }

      form.handleSubmit();
    };

    const loading = promptsVariables.isPending || evalsVariables.isPending;

    return (
      <>
        <DialogContent>
          <Box className="flex flex-col gap-4 mt-2">
            <form.AppField name="info.name">
              {(field) => (
                <TextField
                  label="Experiment Name"
                  variant="filled"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  error={field.state.meta.errors.length > 0}
                  helperText={field.state.meta.errors[0]?.message}
                />
              )}
            </form.AppField>
            <form.AppField name="info.description">
              {(field) => (
                <TextField
                  label="Description"
                  variant="filled"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  error={field.state.meta.errors.length > 0}
                  helperText={field.state.meta.errors[0]?.message}
                />
              )}
            </form.AppField>
            <PromptSelector form={form} />
            <DatasetSelector form={form} />
            <DatasetRowFilterSection form={form} />
            <form.Field
              name="info.evaluators"
              mode="array"
              listeners={{
                onChange: () => {
                  form.setFieldValue("evalVariableMappings", []);
                },
              }}
            >
              {(field) => {
                return (
                  <EvaluatorsSelector
                    evaluators={field.state.value}
                    onAdd={(value) => {
                      field.pushValue(value);
                    }}
                    onRemove={(index) => {
                      field.removeValue(index);
                    }}
                  />
                );
              }}
            </form.Field>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={onCancel}>Cancel</Button>
          <Box sx={{ flex: 1 }} />
          <Button onClick={handleSubmit} loading={loading} variant="contained">
            Configure Prompts
          </Button>
        </DialogActions>
      </>
    );
  },
});

const PromptSelector = withForm({
  ...createExperimentModalFormOpts,
  render: function Render({ form }) {
    const { task } = useTask();

    const promptName = useStore(form.store, (state) => state.values.info.prompt.name);
    const selectedVersions = useStore(form.store, (state) => state.values.info.prompt.versions);

    const { prompts } = usePrompts(task!.id, {});

    const versionsQuery = usePromptVersions(task!.id, promptName ?? undefined, {
      sort: "desc",
      exclude_deleted: true,
      pageSize: 100,
    });

    useEffect(() => {
      if (versionsQuery.versions.length === 1 && selectedVersions.length === 0) {
        form.setFieldValue("info.prompt.versions", [versionsQuery.versions[0].version]);
      }
    }, [versionsQuery.versions, selectedVersions, form]);

    return (
      <Stack sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }} gap={2}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Prompt Versions
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 2 }}>
          <form.AppField
            name="info.prompt.name"
            listeners={{
              onChange: () => {
                form.setFieldValue("info.prompt.versions", []);
                form.setFieldValue("promptVariableMappings", []);
              },
            }}
          >
            {(field) => {
              const selected = prompts.find((p) => p.name === field.state.value) ?? null;

              return (
                <Autocomplete
                  options={prompts}
                  getOptionLabel={(option) => option.name}
                  value={selected}
                  onChange={(_, value) => {
                    field.handleChange(value?.name ?? "");
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Prompt"
                      variant="filled"
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]?.message}
                    />
                  )}
                />
              );
            }}
          </form.AppField>
          <form.AppField
            name="info.prompt.versions"
            mode="array"
            listeners={{
              onChange: () => {
                form.setFieldValue("promptVariableMappings", []);
              },
            }}
          >
            {(field) => {
              const selected = versionsQuery.versions.filter((v) => field.state.value.includes(v.version));

              return (
                <Autocomplete
                  multiple
                  fullWidth
                  loading={versionsQuery.isLoading}
                  disabled={!promptName}
                  options={versionsQuery.versions}
                  getOptionLabel={(option) => option.version.toString()}
                  value={selected}
                  onChange={(_, value) => {
                    field.handleChange(value?.map((v) => v.version) ?? []);
                  }}
                  limitTags={2}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Versions"
                      variant="filled"
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]?.message}
                    />
                  )}
                />
              );
            }}
          </form.AppField>
        </Box>
      </Stack>
    );
  },
});

const DatasetSelector = withForm({
  ...createExperimentModalFormOpts,
  render: function Render({ form }) {
    const { task } = useTask();

    const { datasets } = useDatasets(task!.id, { page: 0, pageSize: 100, sortOrder: "desc" });

    const datasetId = useStore(form.store, (state) => state.values.info.dataset.id);

    const versionsQuery = useDatasetVersionHistory(datasetId ?? undefined);

    return (
      <Stack sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }} gap={2}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Dataset
        </Typography>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 2 }}>
          <form.AppField
            name="info.dataset.id"
            listeners={{
              onChange: () => {
                form.setFieldValue("info.dataset.version", null);
              },
            }}
          >
            {(field) => {
              const selected = datasets.find((d) => d.id === field.state.value) ?? null;

              return (
                <Autocomplete
                  options={datasets}
                  getOptionLabel={(option) => option.name}
                  value={selected}
                  onChange={(_, value) => {
                    field.handleChange(value?.id ?? "");
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Dataset"
                      variant="filled"
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]?.message}
                    />
                  )}
                />
              );
            }}
          </form.AppField>
          <form.AppField name="info.dataset.version">
            {(field) => {
              const selected = versionsQuery.versions.find((v) => v.version_number === field.state.value) ?? null;
              return (
                <Autocomplete
                  options={versionsQuery.versions}
                  disabled={!datasetId}
                  getOptionLabel={(option) => option.version_number.toString()}
                  value={selected}
                  onChange={(_, value) => {
                    field.handleChange(value?.version_number ?? null);
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Version"
                      variant="filled"
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]?.message}
                    />
                  )}
                />
              );
            }}
          </form.AppField>
        </Box>
      </Stack>
    );
  },
});

const DatasetRowFilterSection = withForm({
  ...createExperimentModalFormOpts,
  render: function Render({ form }) {
    const dataset = useStore(form.store, (state) => state.values.info.dataset);
    const versionQuery = useDatasetVersionData(dataset.id ?? undefined, dataset.version ?? undefined);
    const columnNames = versionQuery.version?.column_names ?? [];

    if (!dataset.id || !dataset.version || columnNames.length === 0) {
      return null;
    }

    return (
      <Stack sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }} gap={2}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Stack direction="row" alignItems="center" gap={1}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              Dataset Row Filter
            </Typography>
            <Typography variant="caption" color="text.secondary">
              (Optional)
            </Typography>
            <Tooltip title="Filter which dataset rows to include. Only rows matching ALL conditions will be used." arrow placement="right">
              <InfoOutlinedIcon sx={{ fontSize: 16, color: "text.secondary", cursor: "help" }} />
            </Tooltip>
          </Stack>
        </Stack>
        <form.Field name="datasetRowFilter" mode="array">
          {(field) => (
            <Stack gap={2}>
              {field.state.value.map((_filter, index) => (
                <Stack key={index} direction="row" gap={2} alignItems="center">
                  <form.AppField name={`datasetRowFilter[${index}].column_name`}>
                    {(subField) => (
                      <Autocomplete
                        size="small"
                        options={columnNames}
                        value={subField.state.value || null}
                        onChange={(_, value) => subField.handleChange(value ?? "")}
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            label="Column"
                            variant="filled"
                            error={subField.state.meta.errors.length > 0}
                            helperText={subField.state.meta.errors[0]?.message}
                          />
                        )}
                        sx={{ flex: 1 }}
                      />
                    )}
                  </form.AppField>
                  <form.AppField name={`datasetRowFilter[${index}].column_value`}>
                    {(subField) => (
                      <TextField
                        size="small"
                        label="Value"
                        value={subField.state.value}
                        onChange={(e) => subField.handleChange(e.target.value)}
                        variant="filled"
                        error={subField.state.meta.errors.length > 0}
                        helperText={subField.state.meta.errors[0]?.message}
                        sx={{ flex: 1 }}
                      />
                    )}
                  </form.AppField>
                  <IconButton size="small" color="error" onClick={() => field.removeValue(index)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Stack>
              ))}
              <Button
                variant="outlined"
                size="small"
                startIcon={<AddIcon />}
                onClick={() => field.pushValue({ column_name: "", column_value: "" })}
                sx={{ alignSelf: "flex-start" }}
              >
                Add Filter Condition
              </Button>
            </Stack>
          )}
        </form.Field>
      </Stack>
    );
  },
});

type Evaluator = CreateExperimentModalFormValues["info"]["evaluators"][number];

const EvaluatorsSelector = ({
  evaluators,
  onAdd,
  onRemove,
}: {
  evaluators: Evaluator[];
  onAdd: (evaluator: Evaluator) => void;
  onRemove: (index: number) => void;
}) => {
  const [draft, setDraft] = useState<Evaluator | null>(null);
  const { task } = useTask();

  const evalsQuery = useEvals(task!.id, {});

  const selected = evalsQuery.evals.find((e) => e.name === draft?.name) ?? null;

  const versionsQuery = useEvalVersions(task!.id, selected?.name ?? undefined, {});

  const selectedVersion = versionsQuery.versions.find((v) => v.version === draft?.version) ?? null;

  const canAdd = !evaluators.some((e) => e.name === draft?.name && e.version === draft?.version);

  const handleAdd = () => {
    if (!draft) return;
    onAdd(draft);
    setDraft(null);
  };

  return (
    <>
      <Stack sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }} gap={2}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Evaluators
        </Typography>
        {evaluators.length > 0 && (
          <Stack direction="row" gap={1} flexWrap="wrap">
            {evaluators.map((evaluator, index) => {
              return <Chip key={evaluator.name} label={`${evaluator.name} (v${evaluator.version})`} onDelete={() => onRemove(index)} />;
            })}
          </Stack>
        )}
        <Stack direction="row" gap={1}>
          <Autocomplete
            loading={evalsQuery.isLoading}
            options={evalsQuery.evals}
            getOptionLabel={(option) => option.name}
            value={selected}
            onChange={(_, value) => {
              setDraft({ name: value?.name ?? "", version: null });
            }}
            renderInput={(params) => <TextField {...params} label="Evaluator" variant="filled" />}
            sx={{ flex: 1 }}
          />
          <Autocomplete
            disabled={!selected}
            loading={versionsQuery.isLoading}
            options={versionsQuery.versions}
            getOptionLabel={(option) => option.version.toString()}
            value={selectedVersion}
            onChange={(_, value) => {
              setDraft((old) => ({ name: old?.name ?? "", version: value?.version ?? null }));
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Version"
                error={!canAdd}
                helperText={!canAdd ? "This evaluator and version have already been added" : undefined}
                variant="filled"
              />
            )}
            sx={{ flex: 1 }}
          />
          <Button
            disabled={!selected || !selectedVersion || !canAdd}
            variant="contained"
            color="primary"
            disableElevation
            onClick={handleAdd}
            startIcon={<AddIcon />}
          >
            Add
          </Button>
        </Stack>
      </Stack>
    </>
  );
};
