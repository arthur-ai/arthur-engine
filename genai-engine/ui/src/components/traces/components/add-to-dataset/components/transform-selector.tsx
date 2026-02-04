import { Autocomplete, Stack, TextField, Typography } from "@mui/material";
import { useStore } from "@tanstack/react-form";

import { withFieldGroup } from "../../filtering/hooks/form";
import { useMatchingVariables } from "../hooks/useMatchingVariables";

import { useTransforms } from "@/components/transforms/hooks/useTransforms";
import { useDatasetLatestVersion } from "@/hooks/useDatasetLatestVersion";
import { useTask } from "@/hooks/useTask";
import { DatasetVersionMetadataResponse, TraceTransformResponse } from "@/lib/api-client/api-client";

export const TransformSelector = withFieldGroup({
  defaultValues: {} as {
    dataset: string;
    transform: string;
  },
  render: function Render({ group }) {
    const { task } = useTask();
    const dataset = useStore(group.store, (state) => state.values.dataset);

    const { latestVersion } = useDatasetLatestVersion(dataset);
    const { data: transforms } = useTransforms(task?.id);

    return (
      <group.Field name="transform">
        {(field) => {
          const selected = transforms?.find((t) => t.id === field.state.value) ?? null;

          return (
            <Autocomplete
              options={transforms ?? []}
              value={selected}
              disabled={!dataset}
              disablePortal
              sx={{ flex: 1 }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Transform"
                  helperText={
                    !dataset ? "Select a dataset first" : !transforms ? "No transforms available for this dataset" : "Select a saved transform"
                  }
                />
              )}
              onChange={async (_event, value) => {
                const transformId = value?.id ?? "";
                field.handleChange(transformId);

                // // TODO: Move the logic to `listeners`
                // if (transformId && value && selectedDataset && traceId) {
                //   try {
                //     const response = await api.api.executeTraceTransformExtractionApiV1TracesTraceIdTransformsTransformIdExtractionsPost(
                //       traceId,
                //       transformId
                //     );

                //     if (response.data.variables && response.data.variables.length > 0) {
                //       // Map extracted variables with path information from transform definition
                //       const executedColumns = response.data.variables.map((variable) => {
                //         const variableDef = value.definition.variables.find((v) => v.variable_name === variable.name);

                //         if (!variableDef) {
                //           return {
                //             name: variable.name,
                //             value: variable.value,
                //             path: "",
                //             span_name: "",
                //             attribute_path: "",
                //           };
                //         }

                //         // Validate that the path exists in the trace data
                //         const span = flatSpans.find((s) => s.span_name === variableDef.span_name);
                //         let validatedPath = "";
                //         let validatedSpanName = "";
                //         let validatedAttributePath = "";

                //         if (span) {
                //           // Check if the attribute path exists
                //           const data = getNestedValue(span.raw_data, variableDef.attribute_path);
                //           if (data !== undefined) {
                //             validatedPath = `${variableDef.span_name}.${variableDef.attribute_path}`;
                //             validatedSpanName = variableDef.span_name;
                //             validatedAttributePath = variableDef.attribute_path;
                //           }
                //         }

                //         return {
                //           name: variable.name,
                //           value: variable.value,
                //           path: validatedPath,
                //           span_name: validatedSpanName,
                //           attribute_path: validatedAttributePath,
                //         };
                //       });

                //       const existingDatasetColumns = latestVersion?.column_names || [];
                //       const executedColumnNames = new Set(executedColumns.map((col) => col.name));

                //       // Create columns for dataset columns that aren't in the transform
                //       const datasetOnlyColumns = existingDatasetColumns
                //         .filter((columnName) => !executedColumnNames.has(columnName))
                //         .map((columnName) => ({
                //           name: columnName,
                //           value: "",
                //           path: "",
                //           span_name: "",
                //           attribute_path: "",
                //         }));

                //       form.setFieldValue("columns", [...executedColumns, ...datasetOnlyColumns]);
                //     }
                //   } catch (error) {
                //     console.error("Failed to execute transform:", error);
                //     snackbar.showSnackbar("Failed to execute transform", "error");
                //     form.setFieldValue("columns", []);
                //   }
                // } else {
                //   form.setFieldValue("columns", []);
                // }
              }}
              renderOption={(props, option) => {
                return (
                  <li {...props} key={option.id}>
                    <SelectorOption option={option} dataset={latestVersion!} />
                  </li>
                );
              }}
              getOptionLabel={(option) => option.name}
            />
          );
        }}
      </group.Field>
    );
  },
});

const SelectorOption = ({ option, dataset }: { option: TraceTransformResponse; dataset: DatasetVersionMetadataResponse }) => {
  const { matchCount } = useMatchingVariables({
    columnNames: dataset?.column_names ?? [],
    variables: option.definition.variables ?? [],
  });

  return (
    <Stack>
      <Typography variant="body2" fontWeight="medium">
        {option.name}
      </Typography>
      {option.description && (
        <Typography variant="body2" color="text.secondary">
          {option.description}
        </Typography>
      )}
      <Typography variant="body2" className="text-blue-400">
        {matchCount} of {option.definition.variables.length} variables match
      </Typography>
    </Stack>
  );
};
