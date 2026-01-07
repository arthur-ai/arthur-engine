import { Autocomplete, Divider, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { newAgentExperimentFormOpts } from "../form";

import { withForm } from "@/components/traces/components/filtering/hooks/form";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";

export const BodyMapper = withForm({
  ...newAgentExperimentFormOpts,
  render: function Render({ form }) {
    const datasetRef = useStore(form.store, (state) => state.values.datasetRef);

    const hasVariables = useStore(form.store, (state) => state.values.templateVariableMapping.length > 0);

    const { version } = useDatasetVersionData(datasetRef.id ?? undefined, datasetRef.version ?? undefined);

    if (!hasVariables || !version) return null;

    return (
      <Stack component={Paper} variant="outlined" p={2} gap={2} divider={<Divider />}>
        <Stack gap={2}>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Endpoint Template Variables Mapper
          </Typography>
          <form.AppField name="templateVariableMapping" mode="array">
            {(field) =>
              field.state.value.map((variable, index) => (
                <Stack component={Paper} variant="outlined" p={2} gap={2} key={`${variable}-${index}`}>
                  <Typography variant="body2" color="text.primary" fontWeight="bold">
                    {variable.variable_name}
                  </Typography>
                  <form.AppField key={`${variable}-${index}`} name={`templateVariableMapping[${index}]`}>
                    {() => (
                      <Stack>
                        <Stack direction="row" gap={2}>
                          <form.AppField name={`templateVariableMapping[${index}].source.type`} defaultValue="dataset_column">
                            {(field) => (
                              <TextField
                                select
                                label="Source Type"
                                size="small"
                                value={field.state.value}
                                onChange={(e) => field.handleChange(e.target.value as "dataset_column" | "generated" | "request_time_parameter")}
                                sx={{ flex: 1 }}
                              >
                                <MenuItem value="dataset_column">Dataset Column</MenuItem>
                                <MenuItem value="generated">Generated</MenuItem>
                                <MenuItem value="request_time_parameter">Request Time Parameter</MenuItem>
                              </TextField>
                            )}
                          </form.AppField>
                          <form.AppField name={`templateVariableMapping[${index}].source`}>
                            {(field) => {
                              if (field.state.value.type === "generated") return null;
                              if (field.state.value.type === "request_time_parameter")
                                return <BodyMapperRequestTimeInput form={form} index={index} />;

                              return <BodyMapperDatasetColumnSelector form={form} index={index} />;
                            }}
                          </form.AppField>
                        </Stack>
                      </Stack>
                    )}
                  </form.AppField>
                </Stack>
              ))
            }
          </form.AppField>
        </Stack>
      </Stack>
    );
  },
});

const BodyMapperDatasetColumnSelector = withForm({
  ...newAgentExperimentFormOpts,
  props: {} as {
    index: number;
  },
  render: function Render({ form, index }) {
    const datasetRef = useStore(form.store, (state) => state.values.datasetRef);
    const { version } = useDatasetVersionData(datasetRef.id ?? undefined, datasetRef.version ?? undefined);

    if (!version) return null;

    return (
      <form.AppField name={`templateVariableMapping[${index}].source.dataset_column.name`}>
        {(field) => (
          <Autocomplete
            size="small"
            options={version.column_names}
            getOptionLabel={(option) => option}
            value={field.state.value}
            onChange={(_, value) => field.handleChange(value ?? "")}
            renderInput={(params) => <TextField {...params} label="Dataset Column" />}
            sx={{ flex: 1 }}
          />
        )}
      </form.AppField>
    );
  },
});

const BodyMapperRequestTimeInput = withForm({
  ...newAgentExperimentFormOpts,
  props: {} as {
    index: number;
  },
  render: function Render({ form, index }) {
    return (
      <form.AppField name={`templateVariableMapping[${index}].source.parameter_value`}>
        {(field) => (
          <TextField
            size="small"
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value)}
            sx={{ flex: 1 }}
            label="Request Time Parameter"
          />
        )}
      </form.AppField>
    );
  },
});
