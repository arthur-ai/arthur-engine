import AddIcon from "@mui/icons-material/Add";
import { Autocomplete, Box, Button, Chip, DialogActions, DialogContent, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import { useState } from "react";

import { createExperimentModalFormOpts, CreateExperimentModalFormValues } from "../../form";
import { useGetEvalVariables } from "../../hooks/useGetEvalVaraibles";
import { useGetPromptsVariables } from "../../hooks/useGetPromptsVariables";

import { useEvals } from "@/components/evaluators/hooks/useEvals";
import { useEvalVersions } from "@/components/evaluators/hooks/useEvalVersions";
import { usePrompts } from "@/components/prompts-management/hooks/usePrompts";
import { usePromptVersions } from "@/components/prompts-management/hooks/usePromptVersions";
import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasets } from "@/hooks/useDatasets";
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

    const handleSubmit = async () => {
      const state = form.state.values;

      const { prompt, evaluators } = state.info;

      const [promptVariables, evalVariables] = await Promise.all([
        promptsVariables.getVariables({ name: prompt.name, versions: prompt.versions }),
        evalsVariables.getVariables(evaluators.filter((e) => e.version !== null).map((e) => ({ name: e.name, version: e.version! }))),
      ]);

      if (state.promptVariableMappings.length === 0) {
        form.setFieldValue(
          "promptVariableMappings",
          promptVariables.map((variable) => ({
            target: variable,
            source: "",
          }))
        );
      }

      form.setFieldValue(
        "evalVariableMappings",
        evalVariables.map(({ name, version, variables }) => ({
          name,
          version: version ?? 1,
          variables: variables.map((variable) => ({
            name: variable!,
            sourceType: "dataset_column",
            source: "",
          })),
        }))
      );

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
            <form.Field name="info.evaluators" mode="array">
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

    const { prompts } = usePrompts(task!.id, {});

    const versionsQuery = usePromptVersions(task!.id, promptName ?? undefined, {
      sort: "desc",
      exclude_deleted: true,
      pageSize: 100,
    });

    return (
      <Stack sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 2 }} gap={2}>
        <Typography variant="subtitle2" className="font-semibold">
          Prompt Versions
        </Typography>
        <div className="grid grid-cols-2 gap-2">
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
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]?.message}
                    />
                  )}
                />
              );
            }}
          </form.AppField>
        </div>
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
        <Typography variant="subtitle2" className="font-semibold">
          Dataset
        </Typography>
        <div className="grid grid-cols-2 gap-2">
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
                    field.handleChange(value?.id ?? null);
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Dataset"
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
                  getOptionLabel={(option) => option.version_number.toString()}
                  value={selected}
                  onChange={(_, value) => {
                    field.handleChange(value?.version_number ?? null);
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Version"
                      error={field.state.meta.errors.length > 0}
                      helperText={field.state.meta.errors[0]?.message}
                    />
                  )}
                />
              );
            }}
          </form.AppField>
        </div>
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
        <Typography variant="subtitle2" className="font-semibold">
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
            renderInput={(params) => <TextField {...params} label="Evaluator" />}
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
