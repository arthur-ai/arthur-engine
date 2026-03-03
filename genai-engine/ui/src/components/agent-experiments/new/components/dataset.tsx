import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import { Autocomplete, Button, Divider, IconButton, Paper, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";
import z from "zod";

import { NewAgentExperimentFormData } from "../form";

import { withFieldGroup } from "@arthur/shared-components";
import { useDatasets } from "@/hooks/useDatasets";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";
import { useDatasetVersionHistory } from "@/hooks/useDatasetVersionHistory";
import { useTask } from "@/hooks/useTask";

export const DatasetSetup = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "datasetRef" | "datasetRowFilter">,
  render: function Render({ group }) {
    const { task } = useTask();
    const { datasets } = useDatasets(task!.id, { page: 0, pageSize: 100, sortOrder: "desc" });

    const id = useStore(group.store, (state) => state.values.datasetRef.id);

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
          <group.AppField
            name="datasetRef.id"
            listeners={{
              onChange: ({ value }) => {
                const dataset = datasets.find((d) => d.id === value) ?? null;
                group.setFieldValue("datasetRef.version", dataset?.latest_version_number ?? null);
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
          </group.AppField>
          <group.AppField name="datasetRef.version">
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
          </group.AppField>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <DatasetRowFilters
          form={group}
          fields={{
            datasetRowFilter: "datasetRowFilter",
            datasetRef: "datasetRef",
          }}
        />
      </Stack>
    );
  },
});

const DatasetRowFilters = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "datasetRowFilter" | "datasetRef">,
  render: function Render({ group }) {
    const datasetRef = useStore(group.store, (state) => state.values.datasetRef);

    const { version } = useDatasetVersionData(datasetRef.id ?? undefined, datasetRef.version ?? undefined);

    if (!version) return null;

    return (
      <group.AppField name="datasetRowFilter" mode="array">
        {(field) => (
          <>
            <Stack direction="row" gap={2} alignItems="center" justifyContent="space-between">
              <Stack>
                <Typography variant="body2" color="text.primary" fontWeight="bold">
                  Dataset Row Filters
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Filter the dataset rows that will be used for this experiment.
                </Typography>
              </Stack>
              <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={() => field.pushValue({ column_name: "", column_value: "" })}>
                Add Filter Condition
              </Button>
            </Stack>
            <Divider sx={{ my: 2 }} />
            <Stack gap={2}>
              {field.state.value.length > 0 ? (
                field.state.value.map((item, index) => (
                  <Stack key={index} direction="row" gap={2} alignItems="center">
                    <group.AppField
                      name={`datasetRowFilter[${index}].column_name`}
                      validators={{ onChange: z.string().min(1, "Column is required") }}
                    >
                      {(field) => {
                        return (
                          <Autocomplete
                            size="small"
                            options={version.column_names}
                            getOptionLabel={(option) => option}
                            value={field.state.value}
                            onChange={(_, value) => {
                              field.handleChange(value ?? "");
                            }}
                            renderInput={(params) => <TextField {...params} label="Column" error={field.state.meta.errors.length > 0} />}
                            sx={{ flex: 1 }}
                          />
                        );
                      }}
                    </group.AppField>
                    <group.AppField name={`datasetRowFilter[${index}].column_value`}>
                      {(field) => {
                        return (
                          <TextField
                            size="small"
                            value={field.state.value}
                            onChange={(e) => field.handleChange(e.target.value)}
                            label="Value"
                            sx={{ flex: 1 }}
                          />
                        );
                      }}
                    </group.AppField>
                    <IconButton size="small" color="error" onClick={() => field.removeValue(index)}>
                      <DeleteIcon />
                    </IconButton>
                  </Stack>
                ))
              ) : (
                <div className="flex items-center justify-center py-8 border border-dashed border-neutral-200 rounded-md">
                  <Typography variant="body2" color="text.secondary">
                    No filters added yet
                  </Typography>
                </div>
              )}
            </Stack>
          </>
        )}
      </group.AppField>
    );
  },
});
