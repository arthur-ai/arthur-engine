import { Autocomplete, Divider, Paper, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { newAgentExperimentFormOpts } from "../form";

import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasets } from "@/hooks/useDatasets";
import { useDatasetVersionHistory } from "@/hooks/useDatasetVersionHistory";
import { useTask } from "@/hooks/useTask";

export const DatasetSetup = withForm({
  ...newAgentExperimentFormOpts,
  render: function Render({ form }) {
    const { task } = useTask();
    const { datasets } = useDatasets(task!.id, { page: 0, pageSize: 100, sortOrder: "desc" });

    const id = useStore(form.store, (state) => state.values.datasetRef.id);

    const { versions } = useDatasetVersionHistory(id ?? undefined);

    return (
      <Stack component={Paper} variant="outlined" p={2}>
        <Stack>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Select Dataset
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Choose the dataset and version for this experiment.
          </Typography>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Stack gap={2} direction="row">
          <form.AppField
            name="datasetRef.id"
            listeners={{
              onChange: ({ value }) => {
                const dataset = datasets.find((d) => d.id === value) ?? null;
                form.setFieldValue("datasetRef.version", dataset?.latest_version_number ?? null);
              },
            }}
          >
            {(field) => {
              const selected = datasets.find((d) => d.id === field.state.value) ?? null;

              return (
                <Autocomplete
                  size="small"
                  options={datasets}
                  value={selected}
                  getOptionLabel={(option) => option.name}
                  renderInput={(params) => <TextField {...params} label="Dataset" />}
                  onChange={(_, value) => {
                    field.handleChange(value?.id ?? null);
                  }}
                  sx={{ flex: 1 }}
                />
              );
            }}
          </form.AppField>
          <form.AppField name="datasetRef.version">
            {(field) => {
              const selected = versions.find((v) => v.version_number === field.state.value) ?? null;

              return (
                <Autocomplete
                  size="small"
                  disabled={!id}
                  options={versions}
                  getOptionLabel={(option) => `v${option.version_number}`}
                  value={selected}
                  renderInput={(params) => <TextField {...params} label="Version" />}
                  sx={{ flex: 1 }}
                />
              );
            }}
          </form.AppField>
        </Stack>
      </Stack>
    );
  },
});
