import { Autocomplete, Divider, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { NewAgentExperimentFormData } from "../form";

import { withFieldGroup } from "@/components/traces/components/filtering/hooks/form";
import { useDatasetVersionData } from "@/hooks/useDatasetVersionData";

export const BodyMapper = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "templateVariableMapping" | "datasetRef">,
  render: function Render({ group }) {
    const ready = useStore(group.store, (state) => state.values.datasetRef.version && state.values.templateVariableMapping.length > 0);

    return (
      <Stack component={Paper} variant="outlined" p={2} sx={{ opacity: ready ? 1 : 0.5, pointerEvents: ready ? "auto" : "none" }}>
        <Stack>
          <Typography variant="body2" color="text.primary" fontWeight="bold">
            Endpoint Template Variables Mapper
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Map dataset columns to the template variables used in your endpoint configuration.
          </Typography>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Stack gap={2}>
          {ready ? (
            <group.AppField name="templateVariableMapping" mode="array">
              {(field) =>
                field.state.value.map((_, index) => (
                  <Stack component={Paper} variant="outlined" p={2} gap={2} sx={{ backgroundColor: "var(--color-gray-50)" }} key={`${index}`}>
                    <group.Subscribe selector={(state) => state.values.templateVariableMapping[index].variable_name}>
                      {(variableName) => (
                        <Typography variant="body2" color="text.primary" fontWeight="bold">
                          {variableName}
                        </Typography>
                      )}
                    </group.Subscribe>
                    <group.AppField name={`templateVariableMapping[${index}]`}>
                      {() => (
                        <Stack>
                          <Stack direction="row" gap={2}>
                            <group.AppField
                              name={`templateVariableMapping[${index}].source.type`}
                              listeners={{
                                onChange: ({ value }) => {
                                  if (value === "dataset_column") {
                                    group.setFieldValue(`templateVariableMapping[${index}].source`, {
                                      type: "dataset_column",
                                      dataset_column: { name: "" },
                                    });
                                  } else if (value === "generated") {
                                    group.setFieldValue(`templateVariableMapping[${index}].source`, { type: "generated", generator_type: "uuid" });
                                  } else if (value === "request_time_parameter") {
                                    group.setFieldValue(`templateVariableMapping[${index}].source`, { type: "request_time_parameter" });
                                  }
                                },
                              }}
                            >
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
                            </group.AppField>
                            <group.AppField name={`templateVariableMapping[${index}].source`}>
                              {(field) => {
                                if (field.state.value.type === "request_time_parameter") return null;
                                if (field.state.value.type === "generated")
                                  return (
                                    <BodyMapperGeneratedInput
                                      form={group}
                                      fields={{
                                        templateVariableMapping: "templateVariableMapping",
                                      }}
                                      index={index}
                                    />
                                  );

                                return (
                                  <BodyMapperDatasetColumnSelector
                                    form={group}
                                    fields={{
                                      datasetRef: "datasetRef",
                                      templateVariableMapping: "templateVariableMapping",
                                    }}
                                    index={index}
                                  />
                                );
                              }}
                            </group.AppField>
                          </Stack>
                        </Stack>
                      )}
                    </group.AppField>
                  </Stack>
                ))
              }
            </group.AppField>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No variables to map or no dataset version selected
            </Typography>
          )}
        </Stack>
      </Stack>
    );
  },
});

const BodyMapperDatasetColumnSelector = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "templateVariableMapping" | "datasetRef">,
  props: {} as {
    index: number;
  },
  render: function Render({ group, index }) {
    const datasetRef = useStore(group.store, (state) => state.values.datasetRef);
    const { version } = useDatasetVersionData(datasetRef.id ?? undefined, datasetRef.version ?? undefined);

    if (!version) return null;

    return (
      <group.AppField name={`templateVariableMapping[${index}].source.dataset_column.name`}>
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
      </group.AppField>
    );
  },
});

const BodyMapperGeneratedInput = withFieldGroup({
  defaultValues: {} as Pick<NewAgentExperimentFormData, "templateVariableMapping">,
  props: {} as {
    index: number;
  },
  render: function Render({ group, index }) {
    return (
      <group.AppField name={`templateVariableMapping[${index}].source.generator_type`} defaultValue="uuid">
        {(field) => (
          <TextField
            size="small"
            select
            value={field.state.value}
            onChange={(e) => field.handleChange(e.target.value as "uuid")}
            sx={{ flex: 1 }}
            label="Generator Type"
          >
            <MenuItem value="uuid">UUID</MenuItem>
            <MenuItem value="session_id">Session ID</MenuItem>
          </TextField>
        )}
      </group.AppField>
    );
  },
});
